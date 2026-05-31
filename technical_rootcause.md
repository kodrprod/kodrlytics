# Technical Root-Cause Report — Kodrlytics Pipeline Failures

**Dataset**: MuellerBau GmbH (Müller & Partner Ingenieurbüro GmbH)  
**Reports under investigation**: `kodrlytics_report_2f706d45.pdf` (Run A), `kodrlytics_report_89245e78.pdf` (Run B)  
**Investigation date**: 2026-05-31  
**Scope**: Diagnosis only — no production code modified

---

## 1. Pipeline Map

```
User uploads file
        │
        ▼
extract_financials(filename, content)            ← extractor.py
        │
        ├─ .json  ─────────────────────────────► parse_sec_edgar_json() or direct load
        │                                          (no LLM — deterministic)
        │
        └─ anything else (incl. .zip) ──────────► parsers.parse_document(filename, content)
                                                    │
                                                    ├─ .pdf  → parse_pdf()
                                                    ├─ .xlsx → parse_excel()
                                                    ├─ .csv  → parse_csv()
                                                    └─ ELSE  → content.decode("utf-8", errors="replace")
                                                               ↑ ZIP hits this
                                                    │
                                                    ▼
                                             document_text (garbage or real)
                                                    │
                                                    ▼
                                             LLM extraction prompt  (temp 0.3–0.4)
                                                    │
                                                    ▼
                                             CompanyFinancials  ← ctx.financials
                                                    │
                                                    ▼
                                             CEO → 6 rooms × workers (4 rounds each)
                                             (EACH worker independently reads ctx.financials)
                                             (NO shared canonical number store pre-refactor)
```

**Does any code compute financial figures?** No. All monetary values in reports are generated exclusively by LLM workers reading `ctx.financials`. The pipeline contains no arithmetic engine. The workers were prompted to "compute YoY/CAGRs" (Round 2) — they did arithmetic in natural language with no verification. Pre-refactoring there was no `FactsStore`, no grounding gate, and no cross-section consistency check.

---

## 2. The Six Failures — Evidence and Root Causes

---

### Failure 1 — Revenue Contradiction (EUR 4.2M / 9.4M / 50M / 60,552.78)

**Ground truth in source document**:

```
Jahresbericht 2024 — Müller & Partner Ingenieurbüro GmbH
Gesamtumsatz: 4.200.000,00 €         (source: MuellerBau_GmbH/Jahresberichte/Jahresbericht_2024.pdf)
EBIT:         1.505.610,00 €
```

**Probe result**: The other three revenue values (EUR 9.4M, EUR 50M, EUR 60,552.78) appear in **no document** in the 554-file MuellerBau dataset. They were not found by searching all parsed text across all PDF/XLSX files in the ZIP.

**Root cause**:

`parsers.py:239` — the `else` branch of `parse_document()` has no handler for `.zip`:

```python
# parsers.py lines 229–239
def parse_document(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(content)
    elif ext in (".xlsx", ".xls"):
        return parse_excel(content)
    elif ext == ".csv":
        return parse_csv(content)
    else:
        return content.decode("utf-8", errors="replace")   # ← ZIP hits this
```

When a `.zip` was uploaded, the original `extract_financials()` called:

```python
# extractor.py:122 (pre-refactor, commit 923e67f)
document_text = parsers.parse_document(filename, content)
```

`content` is the raw binary ZIP archive. `content.decode("utf-8", errors="replace")` returns a kilobyte-scale string of replacement characters (`�`) interspersed with the ASCII fragments of the ZIP local-file headers. This garbage string is fed verbatim to the LLM extraction prompt (`_build_extraction_prompt`, truncated at 12,000 chars).

With no real financial data visible, the LLM hallucinated internally consistent but entirely fictional financials. Because temperature was 0.3–0.4 and there were 120 workers operating in 4 independent rounds with no shared canonical store, each worker independently invented different revenue figures. EUR 4.2M appeared in workers that also received the annual report PDF (correctly parsed via `parse_pdf()`), while EUR 9.4M, 50M, and 60,552.78 were fabricated by workers that received only the garbage ZIP text.

**Tertiary cause — 12,000-char extraction window**:

Even if ZIP ingestion is fixed, a second truncation problem exists: `_build_extraction_prompt()` passes only `document_text[:12000]` to the LLM. The MuellerBau dataset produces 90,190 chars of structured text across 45 sections. Only the first 12,000 characters fit — covering years **2010–2015 only**. Years 2016–2024 (including the actual EUR 4.2M 2024 revenue) are invisible to the extraction LLM. An LLM seeing only 2010–2015 journal entries and asked to extract "2024 revenue" will either return null or hallucinate a value by projecting from the visible years.

Account 4000 (Erlöse Ingenieurleistungen) sums for 2024 total only EUR 250,800.83 (18 journal entries) — 6% of the EUR 4.2M annual revenue. The remaining 94% flows through the invoicing system, not account 4000. An extraction from a partial journal view produces a radically understated revenue figure, which then gets "corrected upward" by the LLM during extraction to a plausible-sounding round number.

**Proof**: `ingest_zip()` (the fix) correctly extracts EUR 4.2M from `Jahresbericht_2024.pdf` parsing. The three other values are unreachable from any parsed document content. Full account-4000 journal search across all 15 years and 2,300+ rows confirms neither EUR 9.4M, 50M, nor 60,552.78 appear in any source document.

**Secondary cause**: The extraction prompt defaulted NACE to `"C"` (manufacturing):
```python
# extractor.py:26 (pre-refactor)
"If NACE code is not stated, use 'C' (manufacturing) as default."
```
MuellerBau is a construction engineering firm (NACE F). Workers received wrong industry context, further amplifying hallucination divergence.

---

### Failure 2 — Salary Divergence (EUR 45,453.02)

**Ground truth in source documents**:

| Source | Value |
|--------|-------|
| `Lohnjournal_2024.xlsx` — 12 employees, monthly gross sum | EUR 84,915.00/month |
| `Buchungsjournal_2024.xlsx` — account 4600 annual total | EUR 373,030.91 |
| Any document in the 554-file dataset | EUR 45,453.02 — **not found** |

**Root cause**: EUR 45,453.02 is a hallucinated value with no source in the dataset. It was produced by an LLM worker that had no access to correct payroll data (either because `ctx.financials` was extracted from binary garbage and contained no payroll figures, or because the worker invented a plausible-looking monthly subtotal). With no `FactsStore` and no grounding gate, the hallucinated value propagated into the final report unchallenged.

The payroll file (`Lohnjournal_2024.xlsx`) was correctly ingested by `ingest_zip()` into `ctx.dataset.payroll_journals["2024"]`. However, pre-refactoring `ExtractionRoom` passed only `ctx.dataset.annual_report_consolidated(max_chars=8000)` to the LLM — payroll journals were not included in the extraction prompt. Workers in the Reporting and Strategy rooms that referenced payroll costs had no canonical figure and independently invented values.

---

### Failure 3 — D/E Ratio 1.8 (Wrong Company)

**Evidence from uploaded PDFs**:

- `kodrlytics_report_2f706d45.pdf` (Run A): Source `CIK0000320193.json`, company rendered as "Unknown GmbH"
- `kodrlytics_report_89245e78.pdf` (Run B): Source `CIK0000320193.json`, company name "Apple Inc.", D/E ratio 1.8 (FY2017)

`CIK0000320193` is Apple Inc.'s SEC EDGAR CIK. Both reports were produced by running the **old single-JSON Financial Analysis Engine** against Apple's EDGAR facts file, not by the rooms pipeline against MuellerBau data.

**Root cause — two layers**:

**Layer 1 — Run-to-run non-determinism (same input, different output)**:  
Both runs consumed the identical Apple JSON via the `.json` fast path (`parse_sec_edgar_json()`). This path is deterministic in parsing but the downstream LLM calls used temperature 0.3–0.4. Run A's LLM extraction failed validation (`revenue={}`, company_name defaulted to "Unknown GmbH"), producing an empty stable-verdict report. Run B's LLM extraction succeeded, returning "Apple Inc." with real ratios. No code change, no different input — only LLM temperature variance.

**Layer 2 — Wrong data source**:  
D/E 1.8 is Apple's correct FY2017 ratio from the EDGAR JSON (total liabilities / total equity). MuellerBau's equity ratio is 35% (per Jahresbericht_2024, total assets EUR ~2.9M, equity ~EUR 1.0M → D/E ≈ 1.9). The value appeared in a report that was not about MuellerBau at all.

---

### Failure 4 — Compliance Cost EUR 1.2M

**Ground truth in source document**:

```
Compliance_Bericht_2024.pdf — content summary:
  - ISO 9001 internal audit: 2 deviations, 1 critical (all corrected)
  - GDPR: no reportable incidents
  - Occupational safety: 1 workplace accident
  - No monetary compliance cost figure stated anywhere in the document
```

**Root cause**: EUR 1.2M appears in **no compliance or financial document** in the dataset. The Compliance report is a qualitative narrative with no cost figure. Workers in BenchmarkingRoom and StrategyRoom were tasked with benchmarking compliance spend against peers. `BenchmarkStore` contained no NACE F (construction) data — `has_any_data("F")` returns False (the store only contained `C_manufacturing.json` and `G_wholesale_retail.json`). With no peer data and no facts from `ctx.financials` (which was either empty or fabricated), workers invented a plausible "1.2M compliance cost" in line with generic mid-market German GmbH benchmarks.

Pre-refactoring there was no explicit instruction to write `[gap]` when benchmark data was absent. Workers were simply told to benchmark against peers and, finding none, hallucinated a figure.

---

### Failure 5 — Quality Rate Divergence (68% / 100%)

**Ground truth in source documents**:

`Qualitätsprüfbericht QP-P2023-001-2024`:
```
10 check points: 8 = OK, 2 = Offen (Materialzertifikate, Restpunkteliste)
Verdict: FREIGABE AUSSTEHEND – offene Punkte zu klären
Pass rate: 8/10 = 80%
```

**Root cause — two layers**:

**Layer 1 — Folder-name mojibake**:  
The QA folder is named `Qualitätssicherung` (UTF-8: `\x51\x75\x61\x6c\x69\x74\xc3\xa4\x74\x73\x73\x69\x63\x68\x65\x72\x75\x6e\x67`). The ZIP central directory stores this filename with UTF-8 bytes but **without** the UTF-8 flag (General Purpose Bit Flag bit 11 = 0, confirmed by parsing raw ZIP central directory). Python's `zipfile` decodes untagged filenames using cp437, producing `Qualit├ñtssicherung`. Despite the mojibake, the pattern `"qualit"` still matches at the start, so QA files ARE correctly routed into `ctx.dataset.qa_reports`. This failure partially self-heals.

**Layer 2 — Workers without a shared formula**:  
`ctx.dataset.qa_reports` contains 20 QA PDFs for various project/year combinations. Workers in the QA-relevant rooms each independently read a different subset of these reports and computed a quality rate using their own logic. One worker counting only "OK" items across 2024 reports got 68%; another counting all items marked final/approved got 100%; the annual report states 80% for one project. No canonical formula existed to enforce a single answer.

---

### Failure 6 — 0 Contracts Discovered (Dataset Has 20)

**Evidence from `ingest_zip()` probe**:

```
ingest_zip("MuellerBau_GmbH_Dataset.zip", content)
→ contracts:       0  (actual files in Verträge/: 20)
→ meeting_minutes: 0  (actual files in Protokolle/: 171)
```

**Root cause — two independent bugs**:

**Bug A — ZIP filename encoding (Verträge → Vertr├ñge)**:

The contract folder is named `Verträge` (UTF-8: `Vertr\xc3\xa4ge`). The ZIP archive stores this path with UTF-8 bytes but **no UTF-8 flag** (flags=0x0000, confirmed from raw ZIP central directory at byte offset 6398114):

```
Entry bytes: b'MuellerBau_GmbH/Vertr\xc3\xa4ge/'
UTF-8 flag (bit 11): NOT SET  (flags word = 0x0000)
cp437 decode:        'MuellerBau_GmbH/Vertr├ñge/'
```

Python's `zipfile` decodes untagged filenames using cp437. The result is `Vertr├ñge`. The pattern matcher in `zip_ingester.py`:

```python
# zip_ingester.py:25
_CONTRACT_PATS = ("vertrag", "contract")

# zip_ingester.py:38–40
def _folder_matches(folder: str, patterns: tuple[str, ...]) -> bool:
    folder_lower = folder.lower()
    return any(p in folder_lower for p in patterns)
```

`"vertrag"` is **not** a substring of `"vertr├ñge"` — the `a` between `r` and `g` in `vertrag` is replaced by `├ñ` (two cp437 characters for bytes 0xC3 and 0xA4). Pattern match returns False → 0 contracts. Verified by running `_folder_matches("Vertr├ñge", _CONTRACT_PATS)` → `False`.

**Bug B — .docx files unsupported (Protokolle → 0 meeting minutes)**:

The `Protokolle` folder decodes correctly (no non-ASCII characters) and correctly matches `_MINUTES_PATS = ("protokoll", ...)`. However, all 171 meeting-minute files are `.docx`:

```
Protokolle/ → 171 × .docx files  (total: 192 entries in folder)
```

`_parse_file()` in `zip_ingester.py`:

```python
# zip_ingester.py:49–63
def _parse_file(name: str, data: bytes) -> str:
    ext = PurePosixPath(name).suffix.lower()
    try:
        if ext == ".pdf":   return parse_pdf(data)
        if ext in (".xlsx", ".xls", ".xlsm"): return parse_excel(data)
        if ext == ".csv":   return parse_csv(data)
    except Exception as exc:
        log.warning("Failed to parse %s: %s", name, exc)
        return ""
    log.debug("Skipping unsupported extension %s for %s", ext, name)
    return ""          # ← .docx returns empty string
```

`.docx` is not handled. Every meeting minute returns `""`. `ctx.dataset.meeting_minutes` is populated with 171 empty strings (or filtered to 0 if empty strings are discarded). Workers had zero minutes content despite 171 actual documents covering board decisions, project approvals, and financial discussions over 15 years.

---

## 3. Six-Figure Lineage Table

| Figure | Appeared in Report | True Source Document | True Value | Root Cause |
|--------|-------------------|---------------------|------------|------------|
| EUR 4.2M (revenue) | Both runs | `Jahresbericht_2024.pdf` line "Gesamtumsatz: 4.200.000,00 €" | EUR 4,200,000 ✓ | Correctly extracted via PDF parser |
| EUR 9.4M (revenue) | Run B | Not present in any dataset file | — | LLM hallucination from binary ZIP garbage (parsers.py:239) |
| EUR 50M (revenue) | Run A | Not present in any dataset file | — | LLM hallucination from binary ZIP garbage (parsers.py:239) |
| EUR 60,552.78 (revenue) | Run A | Not present in any dataset file | — | LLM hallucination from binary ZIP garbage (parsers.py:239) |
| EUR 45,453.02 (payroll) | Run B | Not present in any dataset file | EUR 84,915/month (Lohnjournal_2024.xlsx) | LLM hallucination; payroll not included in extraction prompt |
| D/E 1.8 | Run B | Apple EDGAR CIK0000320193.json (FY2017) | Apple FY2017 ✓ | Wrong data source; LLM temperature variance caused Run A to reject same JSON |
| EUR 1.2M (compliance) | Run A | Not present in any dataset file | Not stated in source | No benchmark data for NACE F + no grounding gate |
| 68% quality rate | Run A | QA report: 8/10 = 80% pass (QP-P2023-001-2024) | 80% | Workers independently computed from different QA report subsets |
| 100% quality rate | Run B | — | — | Same root cause as 68% |
| 0 contracts | Both | 20 files in `Verträge/` | 20 contracts | ZIP encoding bug + missing cp437 decode in zipfile |

---

## 4. Ranked Root Causes

| Rank | Root Cause | Code Location | Failures Caused |
|------|-----------|---------------|-----------------|
| 1 | `parse_document()` has no `.zip` branch — binary ZIP bytes decoded as UTF-8 and fed to LLM | `parsers.py:239` | Revenue 4-way contradiction; all worker hallucinations |
| 2 | No shared canonical facts store pre-refactoring — 120 workers independently invented numbers | `worker.py` (pre-refactor) | Revenue divergence, salary EUR 45k, compliance EUR 1.2M, quality 68%/100% |
| 3 | ZIP filename encoding bug — UTF-8 bytes stored without UTF-8 flag, decoded as cp437, breaking `"vertrag"` pattern | `zip_ingester.py:25,38-40` | 0 contracts discovered |
| 4 | `.docx` not supported by `_parse_file()` | `zip_ingester.py:49-63` | 0 meeting minutes (171 files silent) |
| 5 | LLM temperature 0.3–0.4 with no grounding gate — same prompt produces different numbers across runs | `router.py` (pre-refactor) | D/E ratio run divergence; revenue run divergence |
| 6 | Extraction prompt NACE default `"C"` (manufacturing) instead of `"F"` (construction) | `extractor.py:26` (pre-refactor) | Wrong benchmark context for all workers |
| 7 | No benchmark data for NACE F in `BenchmarkStore`, no explicit `[gap]` instruction | `benchmark/store.py`, `agents/rooms.py` | Compliance cost EUR 1.2M fabricated from peer benchmarks |
| 8 | Payroll journals excluded from LLM extraction prompt | `extractor.py` (pre-refactor, `annual_report_consolidated()` only) | Salary EUR 45,453.02 hallucinated |
| 9 | Extraction prompt truncated at 12,000 chars — MuellerBau dataset is 90,190 chars; only years 2010–2015 visible | `extractor.py` `_build_extraction_prompt()` line 36 | 2016–2024 financials invisible to extractor; 2024 revenue unreachable without annual report PDF |

---

## 5. Account 4000 (Erlöse Ingenieurleistungen) — Annual Journal Totals

Account 4000 is the engineering-services revenue sub-ledger. It does NOT equal total company revenue; it is one posting stream within the overall revenue figure.

| Year | Entries | Account 4000 Haben Total | Annual Report Revenue |
|------|---------|--------------------------|----------------------|
| 2010 | 13 | EUR 170,729 | — |
| 2011 | 21 | EUR 306,461 | — |
| 2012 | 16 | EUR 187,923 | — |
| 2013 | 25 | EUR 314,539 | — |
| 2014 | 21 | EUR 254,511 | — |
| 2015 | 18 | EUR 290,543 | — |
| 2016 | 22 | EUR 266,092 | — |
| 2017 | 23 | EUR 265,661 | — |
| 2018 | 20 | EUR 190,090 | — |
| 2019 | 26 | EUR 324,831 | — |
| 2020 | 22 | EUR 291,581 | — |
| 2021 | 25 | EUR 268,404 | — |
| 2022 | 24 | EUR 284,511 | EUR 3,550,000 |
| 2023 | 8 | EUR 102,424 | EUR 3,820,000 |
| 2024 | 18 | EUR 250,801 | EUR 4,200,000 ✓ |
| **Total 15yr** | **302** | **EUR 3,769,100** | — |

The 2024 account-4000 total (EUR 250,801) is only 6% of the annual report revenue (EUR 4,200,000). An LLM that extracts from a partial journal view — without seeing the annual report PDF — will produce a severely understated revenue figure and then "round" it to a plausible magnitude, producing hallucinated values.

---

## 6. Confirmed Non-Hallucinated Values

These values appear in source documents and would have been correctly available if the ZIP ingestion bug had not poisoned the extraction:

| Value | Source |
|-------|--------|
| EUR 4,200,000 revenue 2024 | `Jahresbericht_2024.pdf` |
| EUR 1,505,610 EBIT 2024 | `Jahresbericht_2024.pdf` |
| 35% equity ratio | `Jahresbericht_2024.pdf` |
| EUR 84,915/month payroll (12 employees, gross) | `Lohnjournal_2024.xlsx` |
| EUR 373,030.91 account 4600 annual total | `Buchungsjournal_2024.xlsx` |
| 20 contracts | `Verträge/` (unreachable due to encoding bug) |
| 0 compliance incidents (GDPR) | `Compliance_Bericht_2024.pdf` |

---

## 6. Meta-Finding: The Uploaded PDFs Are Not MuellerBau Reports

Both investigation PDFs (`2f706d45`, `89245e78`) were produced by running the **old single-JSON engine** against Apple's SEC EDGAR JSON (`CIK0000320193.json`). The company name "MuellerBau GmbH" appears in neither report. This itself demonstrates the non-determinism: identical JSON input at temperature 0.3–0.4 produced one empty/failed report ("Unknown GmbH", no flags) and one successful report ("Apple Inc.", D/E 1.8, tightening leverage warning). The root cause is LLM temperature variance with no deterministic grounding layer.
