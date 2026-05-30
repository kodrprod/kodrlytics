"""Deterministic reconciliation gate: checks accounting identities hold."""
from __future__ import annotations
from backend.schema.models import CompanyFinancials, ReconciliationResult, ReconciliationError


TOLERANCE = 0.01  # 1% relative tolerance for rounding in source docs


def _rel_delta(expected: float, actual: float) -> float:
    if expected == 0:
        return abs(actual)
    return abs(actual - expected) / abs(expected)


def reconcile(financials: CompanyFinancials) -> ReconciliationResult:
    errors: list[ReconciliationError] = []
    bs = financials.balance_sheet
    is_ = financials.income_statement

    for p in bs.periods:
        lbl = p.label

        # 1. Assets = Liabilities + Equity
        total_l_e = bs.total_liabilities.get(lbl, 0) + bs.total_equity.get(lbl, 0)
        total_a = bs.total_assets.get(lbl, 0)
        if _rel_delta(total_a, total_l_e) > TOLERANCE:
            errors.append(ReconciliationError(
                period=lbl, check="assets = liabilities + equity",
                expected=total_a, actual=total_l_e,
                delta=total_l_e - total_a, tolerance=TOLERANCE
            ))

        # 2. Current assets subtotal
        ca_sum = (bs.cash.get(lbl, 0) + bs.accounts_receivable.get(lbl, 0)
                  + bs.inventory.get(lbl, 0) + bs.other_current_assets.get(lbl, 0))
        ca = bs.current_assets.get(lbl, 0)
        if _rel_delta(ca, ca_sum) > TOLERANCE:
            errors.append(ReconciliationError(
                period=lbl, check="current_assets subtotal",
                expected=ca, actual=ca_sum,
                delta=ca_sum - ca, tolerance=TOLERANCE
            ))

        # 3. Current liabilities subtotal
        cl_sum = (bs.accounts_payable.get(lbl, 0) + bs.short_term_debt.get(lbl, 0)
                  + bs.other_current_liabilities.get(lbl, 0))
        cl = bs.current_liabilities.get(lbl, 0)
        if _rel_delta(cl, cl_sum) > TOLERANCE:
            errors.append(ReconciliationError(
                period=lbl, check="current_liabilities subtotal",
                expected=cl, actual=cl_sum,
                delta=cl_sum - cl, tolerance=TOLERANCE
            ))

    for p in is_.periods:
        lbl = p.label

        # 4. Gross profit = Revenue - COGS
        gp_calc = is_.revenue.get(lbl, 0) - is_.cost_of_goods_sold.get(lbl, 0)
        gp = is_.gross_profit.get(lbl, 0)
        if _rel_delta(gp, gp_calc) > TOLERANCE:
            errors.append(ReconciliationError(
                period=lbl, check="gross_profit = revenue - cogs",
                expected=gp, actual=gp_calc,
                delta=gp_calc - gp, tolerance=TOLERANCE
            ))

        # 5. EBIT = Gross profit - Opex
        ebit_calc = is_.gross_profit.get(lbl, 0) - is_.operating_expenses.get(lbl, 0)
        ebit = is_.ebit.get(lbl, 0)
        if _rel_delta(ebit, ebit_calc) > TOLERANCE:
            errors.append(ReconciliationError(
                period=lbl, check="ebit = gross_profit - opex",
                expected=ebit, actual=ebit_calc,
                delta=ebit_calc - ebit, tolerance=TOLERANCE
            ))

        # 6. Net income = EBT - Tax
        ni_calc = is_.ebt.get(lbl, 0) - is_.income_tax.get(lbl, 0)
        ni = is_.net_income.get(lbl, 0)
        if _rel_delta(ni, ni_calc) > TOLERANCE:
            errors.append(ReconciliationError(
                period=lbl, check="net_income = ebt - tax",
                expected=ni, actual=ni_calc,
                delta=ni_calc - ni, tolerance=TOLERANCE
            ))

    return ReconciliationResult(passed=len(errors) == 0, errors=errors)
