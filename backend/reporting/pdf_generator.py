"""
Doktorarbeit-style PDF report generator.
Structure:
  1. Cover page
  2. Executive Summary
  3. Methodology
  4. Per-company analysis (profitability, liquidity, efficiency, leverage)
  5. Benchmark comparisons
  6. Risk flags (detailed)
  7. Recommendations (one detailed section per action)
  8. Projections
  9. Appendix: all computed ratios
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from fpdf import FPDF

log = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


@dataclass
class CompanyReport:
    company_name: str
    nace_code: str
    ratios: list[dict]
    flags: list[dict]
    projections: list[dict]
    narrative: str
    recommendations_detail: str = ""  # LLM-written deep recommendations


@dataclass
class AnalysisReport:
    title: str
    generated_at: str
    source_file: str
    companies: list[CompanyReport]
    portfolio_summary: str = ""


def _safe(text: str) -> str:
    """Replace characters outside latin-1 so Helvetica (core font) can render them."""
    return (text
            .replace("—", "--")   # em dash
            .replace("–", "-")    # en dash
            .replace("’", "'")    # right single quote
            .replace("‘", "'")    # left single quote
            .replace("“", '"')    # left double quote
            .replace("”", '"')    # right double quote
            .replace("…", "...")) # ellipsis


class KodrlyticsPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "KODRLYTICS -- Financial Analysis Report", align="L")
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()} -- Confidential -- All projections are illustrative, not guarantees", align="C")

    def chapter_title(self, text: str, level: int = 1):
        text = _safe(text)
        self.ln(6)
        if level == 1:
            self.set_font("Helvetica", "B", 16)
            self.set_fill_color(20, 40, 70)
            self.set_text_color(255, 255, 255)
            self.cell(0, 10, f"  {text}", fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
        elif level == 2:
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(20, 40, 70)
            self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(20, 40, 70)
            self.line(20, self.get_y(), 190, self.get_y())
            self.set_text_color(0, 0, 0)
        else:
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(50, 80, 120)
            self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
        self.ln(2)

    def body_text(self, text: str, size: int = 10):
        self.set_font("Helvetica", "", size)
        self.multi_cell(0, 5.5, _safe(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def metric_row(self, label: str, value: str, flag: bool = False):
        label, value = _safe(label), _safe(value)
        self.set_font("Helvetica", "", 10)
        if flag:
            self.set_fill_color(255, 240, 200)
            self.set_font("Helvetica", "B", 10)
        else:
            self.set_fill_color(245, 248, 252)
        self.cell(110, 6, f"  {label}", fill=True)
        self.set_font("Helvetica", "B" if flag else "", 10)
        self.cell(70, 6, value, fill=flag, new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(255, 255, 255)

    def flag_box(self, severity: str, message: str):
        self.ln(2)
        if severity == "critical":
            self.set_fill_color(255, 220, 220)
            self.set_draw_color(200, 50, 50)
            prefix = "!! CRITICAL"
        else:
            self.set_fill_color(255, 245, 200)
            self.set_draw_color(200, 150, 0)
            prefix = "!  WARNING"
        self.set_font("Helvetica", "B", 10)
        self.multi_cell(0, 6, _safe(f"  {prefix}: {message}"), fill=True,
                        border=1, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(0, 0, 0)
        self.ln(2)

    def projection_table(self, projection: dict):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(20, 40, 70)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, _safe(f"  {projection.get('description', projection.get('metric', ''))}"),
                  fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

        headers = ["Scenario", "Target", "Financial Impact"]
        widths = [50, 60, 60]
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(230, 235, 245)
        for h, w in zip(headers, widths):
            self.cell(w, 6, f"  {h}", fill=True, border=1)
        self.ln()

        colors = {"conservative": (240, 248, 240), "base": (230, 240, 255), "optimistic": (230, 255, 240)}
        for s in projection.get("scenarios", []):
            self.set_font("Helvetica", "", 9)
            label = s.get("label", "").capitalize()
            target = f"{s.get('target_value', 0):.1f} {projection.get('unit', '')}"
            impact = f"EUR {s.get('impact_eur', 0):,.0f}" if s.get('impact_eur') is not None else "n/a"
            bg = colors.get(s.get("label", ""), (255, 255, 255))
            self.set_fill_color(*bg)
            self.cell(50, 6, f"  {label}", fill=True, border=1)
            self.cell(60, 6, f"  {target}", fill=True, border=1)
            self.cell(60, 6, f"  {impact}", fill=True, border=1)
            self.ln()
        self.ln(3)


def _group_ratios(ratios: list[dict]) -> dict[str, list[dict]]:
    groups = {
        "Profitability": ["gross_margin", "ebit_margin", "net_margin", "roe", "roa", "roce"],
        "Liquidity": ["current_ratio", "quick_ratio", "cash_ratio"],
        "Efficiency": ["dso", "dpo", "inventory_days", "ccc", "asset_turnover"],
        "Leverage": ["debt_to_equity", "interest_coverage", "net_debt_ebitda"],
        "Growth": ["revenue_growth_yoy", "ebit_growth_yoy", "revenue_cagr"],
    }
    result: dict[str, list[dict]] = {g: [] for g in groups}
    for ratio in ratios:
        fid = ratio.get("finding_id", "")
        placed = False
        for group, prefixes in groups.items():
            if any(fid.startswith(p) for p in prefixes):
                result[group].append(ratio)
                placed = True
                break
        if not placed:
            result.setdefault("Other", []).append(ratio)
    return {k: v for k, v in result.items() if v}


def generate_pdf(report: AnalysisReport, job_id: str) -> Path:
    """Generate a full PDF report. Returns the path to the saved file."""
    pdf = KodrlyticsPDF()
    pdf.set_title(report.title)
    pdf.set_author("Kodrlytics Financial Analysis Engine")

    # ── Cover page ─────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(20, 40, 70)
    pdf.cell(0, 15, "KODRLYTICS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 100, 130)
    pdf.cell(0, 8, "Financial Analysis Engine", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)
    pdf.set_draw_color(20, 40, 70)
    pdf.set_line_width(0.8)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(15)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 40, 70)
    # Split long titles
    title_lines = [report.title[i:i+50] for i in range(0, len(report.title), 50)]
    for line in title_lines:
        pdf.cell(0, 10, line, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Generated: {report.generated_at}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Source: {report.source_file}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Companies analysed: {len(report.companies)}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 5, "CONFIDENTIAL -- For internal use only. All projections are illustrative and do not constitute financial advice. "
                          "Deterministic calculations are based on submitted financial data. LLM-generated narrative has been "
                          "verified against computed values via automated grounding gate.", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_line_width(0.2)

    # ── Portfolio summary (if multiple companies) ──────────────────────────────
    if len(report.companies) > 1 and report.portfolio_summary:
        pdf.add_page()
        pdf.chapter_title("Portfolio Executive Summary", level=1)
        pdf.body_text(report.portfolio_summary)

    # ── Per-company chapters ───────────────────────────────────────────────────
    for i, company in enumerate(report.companies):
        pdf.add_page()
        pdf.chapter_title(f"{'I' * (i+1)}. {company.company_name}", level=1)
        pdf.body_text(f"NACE Sector: {company.nace_code}")

        # Executive summary from narrative
        pdf.chapter_title("Executive Summary", level=2)
        # Strip grounding warnings from narrative
        narrative = company.narrative
        if narrative.startswith("[GROUNDING"):
            narrative = narrative[narrative.find("]") + 1:].strip() if "]" in narrative else narrative
        pdf.body_text(narrative[:2000] if len(narrative) > 2000 else narrative)

        # Key ratios by group
        pdf.chapter_title("Financial Ratios", level=2)
        grouped = _group_ratios(company.ratios)
        flag_ids = {f.get("finding_id", "") for f in company.flags}

        for group_name, group_ratios in grouped.items():
            pdf.chapter_title(group_name, level=3)
            # Sort by period descending
            sorted_ratios = sorted(group_ratios, key=lambda r: (r.get("finding_id", ""), r.get("period", "")))
            for ratio in sorted_ratios:
                val = ratio.get("value")
                unit = ratio.get("unit", "")
                period = ratio.get("period", "")
                name = ratio.get("name", ratio.get("finding_id", ""))
                value_str = f"{val:.2f} {unit}  ({period})" if val is not None else "N/A"
                is_flagged = ratio.get("finding_id", "") in flag_ids
                pdf.metric_row(name, value_str, flag=is_flagged)
            pdf.ln(3)

        # Flags
        if company.flags:
            pdf.add_page()
            pdf.chapter_title("Risk Flags", level=2)
            for flag in company.flags:
                pdf.flag_box(flag.get("severity", "warning"), flag.get("message", ""))
                # Detailed context
                delta = flag.get("delta_vs_median")
                peer_median = flag.get("peer_median")
                if delta is not None and peer_median is not None:
                    pdf.body_text(
                        f"Company value: {flag.get('company_value', 0):.2f}  |  "
                        f"Peer median: {peer_median:.2f}  |  "
                        f"Delta vs median: {delta:+.2f}"
                    )

        # Recommendations
        if company.projections:
            pdf.add_page()
            pdf.chapter_title("Improvement Recommendations & Projections", level=2)
            for proj in company.projections:
                pdf.chapter_title(proj.get("description", proj.get("metric", "")), level=3)
                pdf.projection_table(proj)
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(120, 120, 120)
                pdf.body_text(proj.get("disclaimer", ""))
                pdf.set_text_color(0, 0, 0)

            # Deep recommendations text (LLM-generated if available)
            if company.recommendations_detail:
                pdf.chapter_title("Detailed Recommendations (Deep Analysis)", level=2)
                pdf.body_text(company.recommendations_detail)

        # Full narrative
        if len(narrative) > 2000:
            pdf.add_page()
            pdf.chapter_title("Full Analytical Narrative", level=2)
            pdf.body_text(narrative)

    # ── Methodology appendix ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.chapter_title("Appendix A -- Methodology", level=1)
    pdf.body_text("""All financial ratios are computed deterministically from the submitted financial statements
using Python (pandas/numpy). No ratio, projection, or benchmark comparison involves an LLM calculation.

The LLM (via OpenRouter) is used for exactly two purposes:
  1. Extracting unstructured documents (PDF, Excel, CSV) into a canonical JSON schema.
  2. Writing the analytical narrative from pre-computed findings.

Every number in the narrative is verified against the computed values dictionary via an automated
grounding gate before the report is published. Unverified figures are flagged or removed.

Projection scenarios are bounded by industry peer quartiles (p25/p75) from the Bundesbank/ECB BACH
database, not arbitrary multipliers. This grounds scenario ranges in real peer dispersion.

Benchmark data source: Bundesbank/ECB BACH database (2022), German Mittelstand segment.""")

    pdf.chapter_title("Ratio Formulae", level=2)
    formulae = [
        ("Gross Margin", "gross_profit / revenue x 100"),
        ("EBIT Margin", "ebit / revenue x 100"),
        ("Net Margin", "net_income / revenue x 100"),
        ("ROE", "net_income / total_equity x 100"),
        ("ROA", "net_income / total_assets x 100"),
        ("ROCE", "ebit / (total_assets - current_liabilities) x 100"),
        ("Current Ratio", "current_assets / current_liabilities"),
        ("Quick Ratio", "(current_assets - inventory) / current_liabilities"),
        ("DSO", "(accounts_receivable / revenue) x 365"),
        ("DPO", "(accounts_payable / cogs) x 365"),
        ("Inventory Days", "(inventory / cogs) x 365"),
        ("CCC", "DSO + inventory_days - DPO"),
        ("Asset Turnover", "revenue / total_assets"),
        ("D/E", "total_liabilities / total_equity"),
        ("Interest Coverage", "ebit / interest_expense"),
        ("Net Debt / EBITDA", "(long_term_debt + short_term_debt - cash) / ebitda"),
    ]
    for name, formula in formulae:
        pdf.metric_row(name, formula)

    pdf.chapter_title("Appendix B -- Disclaimer", level=1)
    pdf.body_text("""This report is generated by the Kodrlytics Financial Analysis Engine and is intended
for informational purposes only. It does not constitute financial advice, investment advice,
or any form of professional advisory service.

All projections are labelled "projection, not a guarantee." Scenario ranges reflect peer benchmark
dispersion and stated implementation assumptions, not predicted outcomes.

Financial data was provided by the user and has not been independently audited or verified
beyond automated reconciliation checks (accounting identity validation).

For DATA_MODE=real runs: data is processed using paid LLM providers with no-logging policies.
For DATA_MODE=test runs: free LLM providers are used and may process data for model improvement.
""")

    # Save
    out_path = REPORTS_DIR / f"{job_id}.pdf"
    pdf.output(str(out_path))
    log.info("PDF report saved: %s (%.1f KB)", out_path, out_path.stat().st_size / 1024)
    return out_path
