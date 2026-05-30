import pytest
from pathlib import Path
from backend.schema.models import CompanyFinancials
from backend.analysis.ratios import run_analysis
from backend.benchmark.store import BenchmarkStore
from backend.benchmark.flags import run_benchmark


def _get_store() -> BenchmarkStore:
    data_dir = Path(__file__).parent.parent.parent / "data" / "benchmarks"
    return BenchmarkStore(data_dir=data_dir)


def _sample_financials_with_high_dso() -> CompanyFinancials:
    """Mustermann-like financials with DSO deliberately high to trigger flag."""
    return CompanyFinancials(**{
        "company_name": "HighDSO GmbH",
        "nace_code": "C25",
        "income_statement": {
            "periods": [{"year": 2023, "label": "2023"}],
            "revenue": {"2023": 5_000_000},
            "cost_of_goods_sold": {"2023": 3_000_000},
            "gross_profit": {"2023": 2_000_000},
            "operating_expenses": {"2023": 1_200_000},
            "ebit": {"2023": 800_000},
            "interest_expense": {"2023": 100_000},
            "ebt": {"2023": 700_000},
            "income_tax": {"2023": 210_000},
            "net_income": {"2023": 490_000},
            "depreciation_amortization": {"2023": None},
            "ebitda": {"2023": None},
        },
        "balance_sheet": {
            "periods": [{"year": 2023, "label": "2023"}],
            "cash": {"2023": 200_000},
            "accounts_receivable": {"2023": 1_200_000},  # DSO = 1.2M/5M*365 = 87.6 days (high)
            "inventory": {"2023": 400_000},
            "other_current_assets": {"2023": 50_000},
            "current_assets": {"2023": 1_850_000},
            "fixed_assets": {"2023": 2_000_000},
            "other_noncurrent_assets": {"2023": 150_000},
            "total_assets": {"2023": 4_000_000},
            "accounts_payable": {"2023": 250_000},
            "short_term_debt": {"2023": 150_000},
            "other_current_liabilities": {"2023": 100_000},
            "current_liabilities": {"2023": 500_000},
            "long_term_debt": {"2023": 1_500_000},
            "other_noncurrent_liabilities": {"2023": 200_000},
            "total_liabilities": {"2023": 2_200_000},
            "share_capital": {"2023": 500_000},
            "retained_earnings": {"2023": 1_300_000},
            "total_equity": {"2023": 1_800_000},
        },
    })


def test_store_loads():
    store = _get_store()
    assert len(store.available_nace_codes()) > 0


def test_benchmark_lookup():
    store = _get_store()
    bm = store.get("C25", "dso")
    assert bm is not None
    assert bm.median > 0


def test_nace_prefix_fallback():
    store = _get_store()
    # C25 → should fall back to C if C25 not present
    bm = store.get("C25", "gross_margin")
    assert bm is not None


def test_dso_flag_triggered():
    store = _get_store()
    fin = _sample_financials_with_high_dso()
    analysis = run_analysis(fin)
    bench = run_benchmark(analysis, "C25", store)
    dso_flags = [f for f in bench.flags if f.flag_type == "receivables_slow"]
    assert len(dso_flags) > 0, "Expected DSO flag for high DSO company"


def test_no_spurious_flags_healthy_company():
    """A company with DSO at peer median should not trigger receivables flag."""
    store = _get_store()
    # DSO = 150k / 1M * 365 = 54.75 days — below the C-sector median of ~48 * 1.3 = 62.4
    fin = CompanyFinancials(**{
        "company_name": "Healthy GmbH",
        "nace_code": "C",
        "income_statement": {
            "periods": [{"year": 2023, "label": "2023"}],
            "revenue": {"2023": 1_000_000},
            "cost_of_goods_sold": {"2023": 600_000},
            "gross_profit": {"2023": 400_000},
            "operating_expenses": {"2023": 200_000},
            "ebit": {"2023": 200_000},
            "interest_expense": {"2023": 20_000},
            "ebt": {"2023": 180_000},
            "income_tax": {"2023": 54_000},
            "net_income": {"2023": 126_000},
            "depreciation_amortization": {"2023": 50_000},
            "ebitda": {"2023": 250_000},
        },
        "balance_sheet": {
            "periods": [{"year": 2023, "label": "2023"}],
            "cash": {"2023": 100_000},
            "accounts_receivable": {"2023": 150_000},
            "inventory": {"2023": 80_000},
            "other_current_assets": {"2023": 20_000},
            "current_assets": {"2023": 350_000},
            "fixed_assets": {"2023": 500_000},
            "other_noncurrent_assets": {"2023": 50_000},
            "total_assets": {"2023": 900_000},
            "accounts_payable": {"2023": 80_000},
            "short_term_debt": {"2023": 50_000},
            "other_current_liabilities": {"2023": 20_000},
            "current_liabilities": {"2023": 150_000},
            "long_term_debt": {"2023": 300_000},
            "other_noncurrent_liabilities": {"2023": 50_000},
            "total_liabilities": {"2023": 500_000},
            "share_capital": {"2023": 200_000},
            "retained_earnings": {"2023": 200_000},
            "total_equity": {"2023": 400_000},
        },
    })
    analysis = run_analysis(fin)
    bench = run_benchmark(analysis, "C", store)
    dso_flags = [f for f in bench.flags if f.flag_type == "receivables_slow"]
    assert len(dso_flags) == 0, f"Unexpected DSO flag: {dso_flags}"
