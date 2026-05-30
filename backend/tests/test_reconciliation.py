import pytest
from backend.schema.models import (
    CompanyFinancials, IncomeStatement, BalanceSheet, Period
)
from backend.analysis.reconciliation import reconcile


def _make_financials(override: dict = None) -> CompanyFinancials:
    """Build a minimal, balanced set of financials."""
    data = {
        "company_name": "Test GmbH",
        "nace_code": "C25",
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
    }
    if override:
        # Simple top-level override for testing failures
        for path, val in override.items():
            keys = path.split(".")
            d = data
            for k in keys[:-1]:
                d = d[k]
            d[keys[-1]] = val
    return CompanyFinancials(**data)


def test_clean_financials_pass():
    fin = _make_financials()
    result = reconcile(fin)
    assert result.passed, f"Expected pass, got errors: {result.errors}"


def test_assets_liabilities_mismatch():
    fin = _make_financials({"balance_sheet.total_assets.2023": 999_999})
    result = reconcile(fin)
    assert not result.passed
    checks = [e.check for e in result.errors]
    assert "assets = liabilities + equity" in checks


def test_gross_profit_mismatch():
    fin = _make_financials({"income_statement.gross_profit.2023": 999_999})
    result = reconcile(fin)
    assert not result.passed
    checks = [e.check for e in result.errors]
    assert "gross_profit = revenue - cogs" in checks


def test_net_income_mismatch():
    fin = _make_financials({"income_statement.net_income.2023": 1})
    result = reconcile(fin)
    assert not result.passed
    checks = [e.check for e in result.errors]
    assert "net_income = ebt - tax" in checks
