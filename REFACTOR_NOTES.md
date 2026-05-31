# Kodrlytics Refactor Notes — Board-Grade Accuracy

## Summary

Before: the MuellerBau report stated **2024 revenue as four different values** (EUR 4.2M, EUR 9.4M, EUR 50M, EUR 60,552.78) and contained 8 self-contradictions and 4 arithmetic errors. After this refactor: every number in a report must trace to a deterministic `FactsStore` entry; the grounding gate strips any sentence whose numbers don't verify; the cross-section consistency check audits divergence before rendering.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/facts/facts_store.py` | NEW — `Fact(id, label, value, unit, period, source_ref, kind)` dataclass + `FactsStore` registry + `build_facts_store()` |
| `backend/facts/gate.py` | NEW — `enforce_grounding()`, `cross_section_consistency_check()`, `_parse_num()` with German locale |
| `backend/intake/extractor.py` | ZIP branch: calls `ingest_zip` first; LLM extracts from parsed text not binary; NACE defaults to F for construction |
| `backend/agents/models.py` | Added `facts_store` field to `PipelineContext` |
| `backend/agents/pipeline.py` | Builds/rebuilds `FactsStore` after Analysis/Benchmarking/Strategy; applies grounding to CEO synthesis; passes `facts_store` to PDF |
| `backend/agents/room.py` | Threads `facts_table` to workers/managers; `BATCH_SIZE` 4→6; errors → `[gap]` not raw strings |
| `backend/agents/worker.py` | Removed "Compute YoY/CAGRs" Round 2; 4 rounds→2; facts table injection; untrusted delimiter blocks |
| `backend/agents/manager.py` | Untrusted delimiters on worker results; grounding gate applied to room reports; errors → `[gap]` |
| `backend/agents/rooms.py` | `BenchmarkingRoom.build_context_str`: emits "NO peer benchmark data for NACE F — use [gap]" when no peers exist |
| `backend/benchmark/store.py` | Added `has_any_data(nace_code)` |
| `backend/llm/router.py` | `temperature=0` for both `narrate()` and `reason()`; cache always-on; API key absence → ERROR log |
| `backend/reporting/pdf_generator.py` | Grounding gate on all chapters; verified facts table chapter; `€`→`EUR` encoding fix |
| `data/benchmarks/F_construction.json` | NEW — honest stub with `metrics: {}` (no fake construction benchmarks) |
| `backend/tests/test_report_grounding_e2e.py` | NEW — 10 tests: ZIP quality, grounding gate, consistency check, FactsStore, German locale parsing |
| `backend/tests/fixtures/tiny_co.zip` | NEW — German-formatted accounting fixture for tests |

---

## Before / After: LLM Call Count

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Worker rounds per task | 4 sequential | 2 sequential | −50% |
| Batch size (concurrent) | 4 | 6 | +50% |
| BATCH_SIZE × rounds | 16 LLM calls per batch | 12 per batch | −25% |
| Estimated total (120 workers × 2 rounds + 6 mgr + 2 CEO + extraction) | ~490 | ~254 | **−48%** |
| Temperature (narrate/reason) | 0.3–0.4 | 0.0 | Deterministic |
| Cache mode | test-only | always-on | Full reproducibility |

---

## Before / After: Report Accuracy

| Issue | Before | After |
|-------|--------|-------|
| ZIP bytes passed to LLM | Raw binary → garbage → hallucinated financials | `ingest_zip` → parsed text → correct extraction |
| Revenue contradiction | 4 distinct values (EUR 4.2M / 9.4M / 50M / 60,552.78) | Single value from FactsStore; grounding gate strips divergent sentences |
| "Compute YoY/CAGRs" in Round 2 | LLM does arithmetic → wrong % | Removed; facts table contains pre-computed ratios |
| Construction benchmarks | Invented €300M robotics market, Destatis "24,500 dwellings" | `has_any_data('F') == False` → workers instructed to write `[gap]` |
| EUR encoding | `€` → `?` in PDF (latin-1 corruption) | `€` → `EUR` in `_safe()` |
| Errors as content | `[Round N error: ...]` in PDF | Errors → `[gap — analysis unavailable]` |
| Untrusted injection | DDG snippets / meeting minutes concatenated verbatim | Wrapped in `<<<UNTRUSTED DATA>>>` blocks |
| Cross-room inconsistency | Undetected until PDF | `cross_section_consistency_check()` logs all divergences |
| Grounding gate wired | Existed in `grounding.py` but never called for rooms PDF | `enforce_grounding()` called after every manager report and CEO synthesis |
| NACE construction default | `C` (manufacturing) for all ZIPs | `F` (construction) when company name contains Bau/construction terms |

---

## Test Suite

```
54 tests — 54 passed — 0 failed
```

Tests assert:
- ZIP ingestion returns valid UTF-8 text (not binary garbage)
- Grounding gate flags EUR 50M when only EUR 1.2M is in FactsStore
- Grounding gate passes numbers within 1.5% of a stored fact
- Cross-section consistency flags the same metric with different values across rooms
- FactsStore populated with >5 facts from a minimal set of financials
- `format()` returns EUR-denominated strings and `[gap]` for missing data
- German `1.234.567,89` correctly parses to `1_234_567.89`

---

## Statement

The report now contains **zero ungrounded numbers that are not stripped or marked [gap]** (proved by `enforce_grounding` on every room report, CEO synthesis, and the PDF render pass), and the FactsStore provides a **single deterministic source of truth** that is verified against every numeric token before publication. Cross-section metric mismatches are detected by `cross_section_consistency_check` and logged before render.

The root cause of the MuellerBau contradictions — `parse_document` returning binary garbage for ZIP files, feeding hallucinated financials to 120 workers — is fixed at line 88 of `extractor.py`.
