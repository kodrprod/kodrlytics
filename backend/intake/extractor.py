"""
Intake stage: parse document → LLM extraction → reconciliation gate → CompanyFinancials.

LLM is called ONCE for extraction with a JSON-schema-enforced response.
If reconciliation fails, we retry once with the errors surfaced to the LLM.
Max 2 LLM calls total for this stage.
"""
from __future__ import annotations
import json
import logging
from backend.schema.models import CompanyFinancials, ReconciliationResult
from backend.analysis.reconciliation import reconcile
from backend.intake.schema_prompt import EXTRACTION_SCHEMA
from backend.intake import parsers
from backend.llm import router

log = logging.getLogger(__name__)

MAX_RETRIES = 1  # total retries after first failure = 1 (2 LLM calls max)


def _build_extraction_prompt(document_text: str, company_hint: str = "") -> str:
    hint = f"\nCompany hint: {company_hint}" if company_hint else ""
    return f"""Extract the financial statements from the following document into structured JSON.{hint}

Rules:
- All monetary values in the original currency (typically EUR for German companies).
- Use the exact year labels as period keys (e.g. "2023", "2022").
- If a line item is not present in the source, use null.
- For German HGB filings, cash flow statement is often absent — set cash_flow_statement to null in that case.
- Identify the company name, currency (default EUR), NACE code (if stated), and reporting standard (HGB or IFRS).
- If NACE code is not stated: use "F" for construction/engineering firms, "G" for wholesale/retail, "J" for IT/software, "C" for manufacturing — infer from company name and activities.
- Extract data for ALL years present in the document, prioritising the most recent.

Document:
---
{document_text[:20000]}
---

Return ONLY valid JSON. No markdown, no explanation."""


def _build_retry_prompt(document_text: str, errors: list, attempt: int) -> str:
    error_summary = "\n".join(
        f"  - Period {e.period}: {e.check} — expected {e.expected:,.0f}, got {e.actual:,.0f} (delta {e.delta:+,.0f})"
        for e in errors
    )
    return f"""Your previous extraction had reconciliation errors (accounting identities do not hold):
{error_summary}

Please re-extract the financial statements, correcting these discrepancies.
Check that: gross_profit = revenue - cogs, ebit = gross_profit - operating_expenses,
net_income = ebt - income_tax, current_assets = cash + AR + inventory + other_current_assets,
total_assets = current_assets + fixed_assets + other_noncurrent_assets,
current_liabilities = accounts_payable + short_term_debt + other_current_liabilities,
total_liabilities = current_liabilities + long_term_debt + other_noncurrent_liabilities,
total_assets = total_liabilities + total_equity.

Document (re-reading):
---
{document_text[:12000]}
---

Return ONLY valid JSON matching the required schema."""


class ExtractionResult:
    def __init__(self, financials: CompanyFinancials, reconciliation: ReconciliationResult,
                 llm_calls: int, raw_extracted: dict):
        self.financials = financials
        self.reconciliation = reconciliation
        self.llm_calls = llm_calls
        self.raw_extracted = raw_extracted

    @property
    def passed(self) -> bool:
        return self.reconciliation.passed


def _is_construction_dataset(ctx) -> bool:
    """Heuristic: is this a construction/Baugewerbe company dataset?"""
    name_lower = (ctx.company_name or "").lower()
    construction_terms = ("bau", "construction", "gmbh", "baufirma", "bauunternehmen",
                          "hoch", "tief", "sanierung", "projekt")
    return any(t in name_lower for t in construction_terms)


async def _extract_from_zip(filename: str, content: bytes,
                             company_hint: str) -> "ExtractionResult":
    """
    Extract CompanyFinancials from a ZIP dataset.

    Rather than passing raw ZIP bytes (binary garbage) to the LLM, we first
    call ingest_zip to get structured text, then run LLM extraction on the
    actual human-readable content.
    """
    from backend.intake.zip_ingester import ingest_zip
    ctx = ingest_zip(filename, content)
    log.info("ZIP extraction: company=%r, files=%d, years=%s",
             ctx.company_name, ctx.total_files, ctx.years)

    # Build readable document text from parsed (non-binary) data.
    # Sort most-recent years FIRST so they land within the extraction window.
    doc_parts: list[str] = []

    # Annual reports are the primary P&L source (most recent first)
    for year in sorted(ctx.annual_reports, reverse=True):
        text = ctx.annual_reports[year].strip()
        if text:
            doc_parts.append(f"=== Annual Report {year} ===\n{text}")

    # Accounting journals for cross-reference (most recent first)
    for year in sorted(ctx.accounting_journals, reverse=True):
        text = ctx.accounting_journals[year].strip()
        if text:
            doc_parts.append(f"=== Accounting Journal {year} (sample) ===\n{text}")

    # Payroll data for headcount/salary cross-reference (most recent first)
    for year in sorted(ctx.payroll_journals, reverse=True):
        text = ctx.payroll_journals[year].strip()
        if text:
            doc_parts.append(f"=== Payroll Journal {year} (sample) ===\n{text}")

    if not doc_parts:
        log.warning("ZIP %s: no parseable content — returning gap financials", filename)
        return _gap_extraction_result(ctx.company_name or filename, "F" if _is_construction_dataset(ctx) else "C")

    document_text = "\n\n".join(doc_parts)
    hint = company_hint or ctx.company_name or ""
    log.info("ZIP extraction: %d chars from %d annual reports, %d journals",
             len(document_text), len(ctx.annual_reports), len(ctx.accounting_journals))

    llm_calls = 0
    last_recon: ReconciliationResult | None = None
    last_raw: dict = {}

    for attempt in range(MAX_RETRIES + 1):
        prompt = (
            _build_extraction_prompt(document_text, hint)
            if attempt == 0
            else _build_retry_prompt(document_text, last_recon.errors, attempt)
        )
        log.info("ZIP extraction: LLM attempt %d", attempt + 1)
        raw = await router.extract(prompt, EXTRACTION_SCHEMA)
        llm_calls += 1
        last_raw = raw

        # Default NACE to 'F' (construction) for construction ZIPs, not 'C'
        if _is_construction_dataset(ctx) and raw.get("nace_code", "C") in ("C", ""):
            raw["nace_code"] = "F"

        financials = _build_financials(raw)
        recon = reconcile(financials)
        last_recon = recon

        if recon.passed:
            log.info("ZIP extraction: reconciliation passed on attempt %d", attempt + 1)
            return ExtractionResult(financials, recon, llm_calls, raw)
        log.warning("ZIP extraction: reconciliation failed attempt %d (%d errors)",
                    attempt + 1, len(recon.errors))

    return ExtractionResult(_build_financials(last_raw), last_recon, llm_calls, last_raw)


def _gap_extraction_result(company_name: str, nace_code: str = "C") -> "ExtractionResult":
    """Return an ExtractionResult with all-gap financials — used when no parseable data found."""
    from backend.schema.models import IncomeStatement, BalanceSheet, CompanyFinancials
    fin = CompanyFinancials(
        company_name=company_name,
        currency="EUR",
        nace_code=nace_code,
        reporting_standard="HGB",
        income_statement=IncomeStatement(periods=[]),
        balance_sheet=BalanceSheet(periods=[]),
    )
    recon = ReconciliationResult(passed=True, errors=[])
    return ExtractionResult(fin, recon, llm_calls=0, raw_extracted={})


async def extract_financials(filename: str, content: bytes,
                              company_hint: str = "") -> ExtractionResult:
    """
    Full intake pipeline:
      1. If .zip: use ingest_zip to build structured text, then LLM-extract from text (not binary)
      2. If .json: try direct parse as CompanyFinancials (no LLM needed)
      3. Otherwise: parse document → LLM extraction → reconciliation gate
      4. If reconciliation fails: one retry with errors surfaced
    """
    # ZIP files: must NOT pass raw bytes to LLM (they are binary garbage).
    # Use ingest_zip first to get structured text, then extract from that.
    if filename.lower().endswith(".zip"):
        return await _extract_from_zip(filename, content, company_hint)

    # Fast path: JSON files — either canonical schema or SEC EDGAR XBRL format
    if filename.lower().endswith(".json"):
        try:
            raw = json.loads(content.decode("utf-8"))

            # Detect SEC EDGAR company facts format — parse and return directly (no LLM)
            if "facts" in raw and "entityName" in raw:
                log.info("Intake: detected SEC EDGAR XBRL format in %s", filename)
                raw = parsers.parse_sec_edgar_json(raw)
                log.info("Intake: SEC EDGAR parsed: company=%s, periods=%s",
                         raw.get("company_name"), raw.get("income_statement", {}).get("periods", []))
                financials = _build_financials(raw)
                recon = reconcile(financials)
                log.info("Intake: SEC EDGAR loaded. Periods=%s recon=%s",
                         [p.label for p in financials.income_statement.periods],
                         "PASS" if recon.passed else f"FAIL ({len(recon.errors)} errors)")
                return ExtractionResult(financials, recon, llm_calls=0, raw_extracted=raw)

            financials = _build_financials(raw)

            # Validate: reject silently-empty canonical JSON
            if not financials.income_statement.periods:
                raise ValueError("No financial periods found — JSON does not match canonical schema")
            if not any(financials.income_statement.revenue.values()):
                raise ValueError("All revenue values are zero — extraction produced no data")

            recon = reconcile(financials)
            log.info("Intake: loaded %s directly (no LLM). Periods=%s recon=%s",
                     filename, [p.label for p in financials.income_statement.periods],
                     "PASS" if recon.passed else f"FAIL ({len(recon.errors)} errors)")
            return ExtractionResult(financials, recon, llm_calls=0, raw_extracted=raw)
        except Exception as e:
            log.warning("Intake: direct JSON parse failed (%s), falling back to LLM", e)

    log.info("Intake: parsing %s", filename)
    document_text = parsers.parse_document(filename, content)
    log.info("Intake: extracted %d chars from document", len(document_text))

    llm_calls = 0
    last_recon: ReconciliationResult | None = None
    last_raw: dict = {}

    for attempt in range(MAX_RETRIES + 1):
        if attempt == 0:
            prompt = _build_extraction_prompt(document_text, company_hint)
        else:
            prompt = _build_retry_prompt(document_text, last_recon.errors, attempt)

        log.info("Intake: LLM extraction attempt %d", attempt + 1)
        raw = await router.extract(prompt, EXTRACTION_SCHEMA)
        llm_calls += 1
        last_raw = raw

        # Map null values: replace None in dicts with 0.0 where required, keep as-is for optional
        financials = _build_financials(raw)
        recon = reconcile(financials)
        last_recon = recon

        if recon.passed:
            log.info("Intake: reconciliation passed on attempt %d", attempt + 1)
            return ExtractionResult(financials, recon, llm_calls, raw)

        log.warning("Intake: reconciliation failed (attempt %d): %d errors", attempt + 1, len(recon.errors))

    # Return anyway with failed reconciliation — caller decides
    log.error("Intake: reconciliation still failing after %d attempts", llm_calls)
    return ExtractionResult(_build_financials(last_raw), last_recon, llm_calls, last_raw)


def _build_financials(raw: dict) -> CompanyFinancials:
    """Convert raw extracted dict to CompanyFinancials, handling nulls gracefully."""
    def _clean_dict(d: dict | None) -> dict:
        if not d:
            return {}
        return {k: (v if v is not None else 0.0) for k, v in d.items()}

    def _optional_dict(d: dict | None) -> dict:
        if not d:
            return {}
        return {k: v for k, v in d.items()}

    def _to_periods(raw_periods: list) -> list:
        """Accept both string years ('2023') and Period dicts ({'year':2023,'label':'2023'})."""
        result = []
        for p in raw_periods:
            if isinstance(p, str):
                result.append({"year": int(p), "label": p})
            elif isinstance(p, dict) and "label" not in p and "year" in p:
                result.append({"year": p["year"], "label": str(p["year"])})
            else:
                result.append(p)
        return result

    is_raw = raw.get("income_statement", {})
    bs_raw = raw.get("balance_sheet", {})
    cf_raw = raw.get("cash_flow_statement")

    income = {
        "periods": _to_periods(is_raw.get("periods", [])),
        "revenue":              _clean_dict(is_raw.get("revenue")),
        "cost_of_goods_sold":   _clean_dict(is_raw.get("cost_of_goods_sold")),
        "gross_profit":         _clean_dict(is_raw.get("gross_profit")),
        "operating_expenses":   _clean_dict(is_raw.get("operating_expenses")),
        "ebit":                 _clean_dict(is_raw.get("ebit")),
        "interest_expense":     _clean_dict(is_raw.get("interest_expense")),
        "ebt":                  _clean_dict(is_raw.get("ebt")),
        "income_tax":           _clean_dict(is_raw.get("income_tax")),
        "net_income":           _clean_dict(is_raw.get("net_income")),
        "depreciation_amortization": _optional_dict(is_raw.get("depreciation_amortization", {})),
        "ebitda":               _optional_dict(is_raw.get("ebitda", {})),
    }

    balance = {
        "periods": _to_periods(bs_raw.get("periods", [])),
        "cash":                       _clean_dict(bs_raw.get("cash")),
        "accounts_receivable":        _clean_dict(bs_raw.get("accounts_receivable")),
        "inventory":                  _clean_dict(bs_raw.get("inventory")),
        "other_current_assets":       _clean_dict(bs_raw.get("other_current_assets")),
        "current_assets":             _clean_dict(bs_raw.get("current_assets")),
        "fixed_assets":               _clean_dict(bs_raw.get("fixed_assets")),
        "other_noncurrent_assets":    _clean_dict(bs_raw.get("other_noncurrent_assets")),
        "total_assets":               _clean_dict(bs_raw.get("total_assets")),
        "accounts_payable":           _clean_dict(bs_raw.get("accounts_payable")),
        "short_term_debt":            _clean_dict(bs_raw.get("short_term_debt")),
        "other_current_liabilities":  _clean_dict(bs_raw.get("other_current_liabilities")),
        "current_liabilities":        _clean_dict(bs_raw.get("current_liabilities")),
        "long_term_debt":             _clean_dict(bs_raw.get("long_term_debt")),
        "other_noncurrent_liabilities": _clean_dict(bs_raw.get("other_noncurrent_liabilities")),
        "total_liabilities":          _clean_dict(bs_raw.get("total_liabilities")),
        "share_capital":              _clean_dict(bs_raw.get("share_capital")),
        "retained_earnings":          _clean_dict(bs_raw.get("retained_earnings")),
        "total_equity":               _clean_dict(bs_raw.get("total_equity")),
    }

    data = {
        "company_name": raw.get("company_name", "Unknown GmbH"),
        "currency":     raw.get("currency", "EUR"),
        "nace_code":    raw.get("nace_code", "C"),
        "reporting_standard": raw.get("reporting_standard", "HGB"),
        "income_statement": income,
        "balance_sheet": balance,
    }

    if cf_raw:
        data["cash_flow_statement"] = {
            "periods": cf_raw.get("periods", []),
            "operating_cash_flow": _clean_dict(cf_raw.get("operating_cash_flow")),
            "investing_cash_flow": _clean_dict(cf_raw.get("investing_cash_flow")),
            "financing_cash_flow": _clean_dict(cf_raw.get("financing_cash_flow")),
            "free_cash_flow":      _optional_dict(cf_raw.get("free_cash_flow", {})),
        }

    return CompanyFinancials(**data)
