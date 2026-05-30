"""Tests for the grounding gate's verify_grounding function."""
import pytest
from backend.schema.models import CompanyFinancials
from backend.analysis.ratios import run_analysis
from backend.briefing.grounding import verify_grounding


def _sample_analysis():
    fin = CompanyFinancials(**{
        "company_name": "Grounding Test GmbH",
        "nace_code": "C",
        "income_statement": {
            "periods": [{"year": 2023, "label": "2023"}],
            "revenue": {"2023": 9_800_000},
            "cost_of_goods_sold": {"2023": 6_370_000},
            "gross_profit": {"2023": 3_430_000},
            "operating_expenses": {"2023": 1_666_000},
            "ebit": {"2023": 1_764_000},
            "interest_expense": {"2023": 165_000},
            "ebt": {"2023": 1_599_000},
            "income_tax": {"2023": 479_700},
            "net_income": {"2023": 1_119_300},
            "depreciation_amortization": {"2023": 360_000},
            "ebitda": {"2023": 2_124_000},
        },
        "balance_sheet": {
            "periods": [{"year": 2023, "label": "2023"}],
            "cash": {"2023": 520_000},
            "accounts_receivable": {"2023": 2_090_000},
            "inventory": {"2023": 1_010_000},
            "other_current_assets": {"2023": 130_000},
            "current_assets": {"2023": 3_750_000},
            "fixed_assets": {"2023": 5_100_000},
            "other_noncurrent_assets": {"2023": 340_000},
            "total_assets": {"2023": 9_190_000},
            "accounts_payable": {"2023": 610_000},
            "short_term_debt": {"2023": 540_000},
            "other_current_liabilities": {"2023": 230_000},
            "current_liabilities": {"2023": 1_380_000},
            "long_term_debt": {"2023": 2_600_000},
            "other_noncurrent_liabilities": {"2023": 260_000},
            "total_liabilities": {"2023": 4_240_000},
            "share_capital": {"2023": 1_000_000},
            "retained_earnings": {"2023": 3_950_000},
            "total_equity": {"2023": 4_950_000},
        },
    })
    return run_analysis(fin)


def test_grounded_number_passes():
    analysis = _sample_analysis()
    # gross_margin.2023 = 35.0% exactly
    narrative = "The gross margin was 35.0% in 2023."
    ungrounded = verify_grounding(narrative, analysis)
    assert ungrounded == [], f"Expected no ungrounded, got: {ungrounded}"


def test_hallucinated_number_caught():
    analysis = _sample_analysis()
    narrative = "The company had a gross margin of 123.456% which is outstanding."
    ungrounded = verify_grounding(narrative, analysis)
    assert len(ungrounded) > 0, "123.456% should be flagged as ungrounded"


def test_year_numbers_ignored():
    """Years like 2023, 2022 should not be flagged."""
    analysis = _sample_analysis()
    narrative = "In 2023, the company reported strong results compared to 2022."
    ungrounded = verify_grounding(narrative, analysis)
    assert ungrounded == [], f"Years should not be flagged: {ungrounded}"


def test_millions_scale_accepted():
    """€9.8M should match revenue of 9,800,000."""
    analysis = _sample_analysis()
    narrative = "Revenue reached €9.8M in the reporting year."
    ungrounded = verify_grounding(narrative, analysis)
    assert ungrounded == [], f"€9.8M should match 9800000: {ungrounded}"
