import pytest
from backend.schema.models import CompanyFinancials
from backend.analysis.ratios import run_analysis


def _sample_financials() -> CompanyFinancials:
    return CompanyFinancials(**{
        "company_name": "Test GmbH",
        "nace_code": "C25",
        "income_statement": {
            "periods": [
                {"year": 2021, "label": "2021"},
                {"year": 2022, "label": "2022"},
                {"year": 2023, "label": "2023"},
            ],
            "revenue":              {"2021": 800_000, "2022": 950_000, "2023": 1_000_000},
            "cost_of_goods_sold":   {"2021": 500_000, "2022": 590_000, "2023": 600_000},
            "gross_profit":         {"2021": 300_000, "2022": 360_000, "2023": 400_000},
            "operating_expenses":   {"2021": 150_000, "2022": 170_000, "2023": 200_000},
            "ebit":                 {"2021": 150_000, "2022": 190_000, "2023": 200_000},
            "interest_expense":     {"2021": 15_000,  "2022": 18_000,  "2023": 20_000},
            "ebt":                  {"2021": 135_000, "2022": 172_000, "2023": 180_000},
            "income_tax":           {"2021": 40_500,  "2022": 51_600,  "2023": 54_000},
            "net_income":           {"2021": 94_500,  "2022": 120_400, "2023": 126_000},
            "depreciation_amortization": {"2021": 40_000, "2022": 45_000, "2023": 50_000},
            "ebitda":               {"2021": 190_000, "2022": 235_000, "2023": 250_000},
        },
        "balance_sheet": {
            "periods": [
                {"year": 2021, "label": "2021"},
                {"year": 2022, "label": "2022"},
                {"year": 2023, "label": "2023"},
            ],
            "cash":                     {"2021": 80_000,  "2022": 90_000,  "2023": 100_000},
            "accounts_receivable":      {"2021": 160_000, "2022": 155_000, "2023": 150_000},
            "inventory":                {"2021": 90_000,  "2022": 85_000,  "2023": 80_000},
            "other_current_assets":     {"2021": 15_000,  "2022": 18_000,  "2023": 20_000},
            "current_assets":           {"2021": 345_000, "2022": 348_000, "2023": 350_000},
            "fixed_assets":             {"2021": 450_000, "2022": 475_000, "2023": 500_000},
            "other_noncurrent_assets":  {"2021": 40_000,  "2022": 45_000,  "2023": 50_000},
            "total_assets":             {"2021": 835_000, "2022": 868_000, "2023": 900_000},
            "accounts_payable":         {"2021": 70_000,  "2022": 75_000,  "2023": 80_000},
            "short_term_debt":          {"2021": 40_000,  "2022": 45_000,  "2023": 50_000},
            "other_current_liabilities":{"2021": 15_000,  "2022": 18_000,  "2023": 20_000},
            "current_liabilities":      {"2021": 125_000, "2022": 138_000, "2023": 150_000},
            "long_term_debt":           {"2021": 320_000, "2022": 310_000, "2023": 300_000},
            "other_noncurrent_liabilities": {"2021": 40_000, "2022": 45_000, "2023": 50_000},
            "total_liabilities":        {"2021": 485_000, "2022": 493_000, "2023": 500_000},
            "share_capital":            {"2021": 200_000, "2022": 200_000, "2023": 200_000},
            "retained_earnings":        {"2021": 150_000, "2022": 175_000, "2023": 200_000},
            "total_equity":             {"2021": 350_000, "2022": 375_000, "2023": 400_000},
        },
    })


def test_gross_margin():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("gross_margin.2023")
    assert r is not None
    assert not r.not_derivable
    assert abs(r.value - 40.0) < 0.01  # 400k/1000k = 40%


def test_ebit_margin():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("ebit_margin.2023")
    assert r is not None
    assert abs(r.value - 20.0) < 0.01  # 200k/1000k = 20%


def test_dso():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("dso.2023")
    assert r is not None
    assert abs(r.value - (150_000 / 1_000_000 * 365)) < 0.1  # ~54.75 days


def test_current_ratio():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("current_ratio.2023")
    assert r is not None
    assert abs(r.value - (350_000 / 150_000)) < 0.01  # ~2.33x


def test_ccc():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("ccc.2023")
    assert r is not None
    assert not r.not_derivable
    # DSO + inv_days - DPO
    dso = 150_000 / 1_000_000 * 365
    inv_days = 80_000 / 600_000 * 365
    dpo = 80_000 / 600_000 * 365
    expected = dso + inv_days - dpo
    assert abs(r.value - expected) < 0.5


def test_roe():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("roe.2023")
    assert r is not None
    assert abs(r.value - (126_000 / 400_000 * 100)) < 0.01


def test_growth_yoy():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("revenue_growth_yoy.2023")
    assert r is not None
    expected = (1_000_000 - 950_000) / 950_000 * 100
    assert abs(r.value - expected) < 0.01


def test_cagr():
    fin = _sample_financials()
    result = run_analysis(fin)
    r = result.by_id("revenue_cagr_2yr")
    assert r is not None
    expected = ((1_000_000 / 800_000) ** (1 / 2) - 1) * 100
    assert abs(r.value - expected) < 0.01


def test_missing_cashflow_graceful():
    """Cash flow optional — ratios that need it should mark not_derivable, not crash."""
    fin = _sample_financials()
    assert fin.cash_flow_statement is None
    result = run_analysis(fin)
    # Should complete without error
    assert len(result.ratios) > 10


def test_finding_id_format():
    fin = _sample_financials()
    result = run_analysis(fin)
    for r in result.ratios:
        # Multi-period ratios (e.g. CAGR spanning "2021-2023") use underscore separators;
        # single-period ratios must carry a ".<period>" suffix.
        if "-" not in r.period:
            assert "." in r.finding_id, f"finding_id '{r.finding_id}' missing period suffix"


def test_all_values_dict():
    fin = _sample_financials()
    result = run_analysis(fin)
    vals = result.all_values()
    assert "gross_margin.2023" in vals
    assert isinstance(vals["gross_margin.2023"], float)
