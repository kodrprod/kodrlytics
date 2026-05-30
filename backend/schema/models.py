"""Canonical financial statement schema for German company analysis."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class Period(BaseModel):
    year: int
    label: str  # e.g. "2023", "2022"


class IncomeStatement(BaseModel):
    """Annual P&L. All values in reporting currency (EUR default)."""
    periods: list[Period]
    revenue: dict[str, float]                      # period label -> value
    cost_of_goods_sold: dict[str, float]
    gross_profit: dict[str, float]
    operating_expenses: dict[str, float]           # SGA + other opex (excl. COGS)
    ebit: dict[str, float]
    interest_expense: dict[str, float]             # positive = expense
    ebt: dict[str, float]
    income_tax: dict[str, float]                   # positive = expense
    net_income: dict[str, float]
    depreciation_amortization: dict[str, Optional[float]]  # None = not reported
    ebitda: dict[str, Optional[float]]             # None = not computable


class BalanceSheet(BaseModel):
    """Year-end balance sheet snapshots."""
    periods: list[Period]
    # Current assets
    cash: dict[str, float]
    accounts_receivable: dict[str, float]
    inventory: dict[str, float]
    other_current_assets: dict[str, float]
    current_assets: dict[str, float]
    # Non-current assets
    fixed_assets: dict[str, float]
    other_noncurrent_assets: dict[str, float]
    total_assets: dict[str, float]
    # Current liabilities
    accounts_payable: dict[str, float]
    short_term_debt: dict[str, float]
    other_current_liabilities: dict[str, float]
    current_liabilities: dict[str, float]
    # Non-current liabilities
    long_term_debt: dict[str, float]
    other_noncurrent_liabilities: dict[str, float]
    total_liabilities: dict[str, float]
    # Equity
    share_capital: dict[str, float]
    retained_earnings: dict[str, float]
    total_equity: dict[str, float]


class CashFlowStatement(BaseModel):
    """Optional — not required by HGB for non-capital-market GmbH."""
    periods: list[Period]
    operating_cash_flow: dict[str, float]
    investing_cash_flow: dict[str, float]
    financing_cash_flow: dict[str, float]
    free_cash_flow: dict[str, Optional[float]]     # None = not reported separately


class CompanyFinancials(BaseModel):
    company_name: str
    currency: str = "EUR"
    nace_code: str          # e.g. "C25" (fabricated metal products)
    reporting_standard: str = "HGB"  # HGB or IFRS
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow_statement: Optional[CashFlowStatement] = None


class ReconciliationError(BaseModel):
    period: str
    check: str
    expected: float
    actual: float
    delta: float
    tolerance: float


class ReconciliationResult(BaseModel):
    passed: bool
    errors: list[ReconciliationError]
