"""Integration test: load Mustermann GmbH sample, run full pipeline (no LLM)."""
import json
from pathlib import Path
import pytest
from backend.schema.models import CompanyFinancials
from backend.analysis.reconciliation import reconcile
from backend.analysis.ratios import run_analysis
from backend.benchmark.store import BenchmarkStore
from backend.benchmark.flags import run_benchmark


SAMPLE_PATH = Path(__file__).parent.parent.parent / "data" / "samples" / "mustermann_gmbh.json"
BENCHMARK_DIR = Path(__file__).parent.parent.parent / "data" / "benchmarks"


def load_mustermann() -> CompanyFinancials:
    data = json.loads(SAMPLE_PATH.read_text())
    return CompanyFinancials(**data)


def test_sample_file_exists():
    assert SAMPLE_PATH.exists(), f"Sample file not found: {SAMPLE_PATH}"


def test_mustermann_reconciles():
    fin = load_mustermann()
    result = reconcile(fin)
    assert result.passed, f"Reconciliation failed: {result.errors}"


def test_mustermann_analysis_runs():
    fin = load_mustermann()
    result = run_analysis(fin)
    assert len(result.ratios) > 15
    # Core ratios must be present and derivable
    for rid in ["gross_margin.2023", "ebit_margin.2023", "dso.2023",
                "current_ratio.2023", "debt_to_equity.2023"]:
        r = result.by_id(rid)
        assert r is not None, f"Missing ratio: {rid}"
        assert not r.not_derivable, f"Ratio unexpectedly not derivable: {rid}"


def test_mustermann_benchmark_runs():
    fin = load_mustermann()
    store = BenchmarkStore(data_dir=BENCHMARK_DIR)
    analysis = run_analysis(fin)
    bench = run_benchmark(analysis, fin.nace_code, store)
    assert bench.company_name == fin.company_name
    # Should have benchmarked at least DSO and current_ratio
    assert "dso" in bench.benchmarked_metrics or "current_ratio" in bench.benchmarked_metrics


def test_all_values_grounding_dict():
    """all_values() should contain at least 10 derivable ratios for grounding gate."""
    fin = load_mustermann()
    analysis = run_analysis(fin)
    vals = analysis.all_values()
    assert len(vals) >= 10, f"Only {len(vals)} derivable ratios — too few for grounding gate"
