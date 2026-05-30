"""Deterministic financial ratio engine. No LLM involved."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from backend.schema.models import CompanyFinancials


@dataclass
class RatioResult:
    finding_id: str          # e.g. "gross_margin.2023"
    name: str
    period: str
    value: Optional[float]
    unit: str                # "%" | "x" | "days" | "EUR"
    formula: str             # human-readable formula string
    not_derivable: bool = False
    not_derivable_reason: str = ""


@dataclass
class AnalysisResult:
    company_name: str
    ratios: list[RatioResult] = field(default_factory=list)
    # Convenience accessors
    def by_id(self, finding_id: str) -> Optional[RatioResult]:
        return next((r for r in self.ratios if r.finding_id == finding_id), None)
    def for_period(self, period: str) -> list[RatioResult]:
        return [r for r in self.ratios if r.period == period]
    def all_values(self) -> dict[str, float]:
        """Returns {finding_id: value} for all derivable ratios — used by grounding gate."""
        return {r.finding_id: r.value for r in self.ratios if not r.not_derivable and r.value is not None}


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def _pct(v: Optional[float]) -> Optional[float]:
    return v * 100 if v is not None else None


def _nd(finding_id: str, name: str, period: str, reason: str) -> RatioResult:
    return RatioResult(
        finding_id=finding_id, name=name, period=period,
        value=None, unit="", formula="",
        not_derivable=True, not_derivable_reason=reason
    )


def run_analysis(financials: CompanyFinancials) -> AnalysisResult:
    result = AnalysisResult(company_name=financials.company_name)
    is_ = financials.income_statement
    bs = financials.balance_sheet
    cf = financials.cash_flow_statement

    periods = [p.label for p in is_.periods]

    # ── Profitability ──────────────────────────────────────────────────────────

    for lbl in periods:
        rev = is_.revenue.get(lbl)
        gp = is_.gross_profit.get(lbl)
        ebit = is_.ebit.get(lbl)
        ni = is_.net_income.get(lbl)
        equity = bs.total_equity.get(lbl)
        assets = bs.total_assets.get(lbl)
        cl = bs.current_liabilities.get(lbl)
        da = is_.depreciation_amortization.get(lbl)
        ebitda_val = is_.ebitda.get(lbl)

        # Compute ebitda if not provided but DA is available
        if ebitda_val is None and ebit is not None and da is not None:
            ebitda_val = ebit + da

        gross_margin = _safe_div(gp, rev)
        result.ratios.append(RatioResult(
            finding_id=f"gross_margin.{lbl}", name="Gross Margin", period=lbl,
            value=_pct(gross_margin), unit="%",
            formula=f"gross_profit / revenue = {gp} / {rev}"
        ) if gross_margin is not None else _nd(f"gross_margin.{lbl}", "Gross Margin", lbl, "missing gross_profit or revenue"))

        ebit_margin = _safe_div(ebit, rev)
        result.ratios.append(RatioResult(
            finding_id=f"ebit_margin.{lbl}", name="EBIT Margin", period=lbl,
            value=_pct(ebit_margin), unit="%",
            formula=f"ebit / revenue = {ebit} / {rev}"
        ) if ebit_margin is not None else _nd(f"ebit_margin.{lbl}", "EBIT Margin", lbl, "missing ebit or revenue"))

        net_margin = _safe_div(ni, rev)
        result.ratios.append(RatioResult(
            finding_id=f"net_margin.{lbl}", name="Net Margin", period=lbl,
            value=_pct(net_margin), unit="%",
            formula=f"net_income / revenue = {ni} / {rev}"
        ) if net_margin is not None else _nd(f"net_margin.{lbl}", "Net Margin", lbl, "missing net_income or revenue"))

        roe = _safe_div(ni, equity)
        result.ratios.append(RatioResult(
            finding_id=f"roe.{lbl}", name="Return on Equity", period=lbl,
            value=_pct(roe), unit="%",
            formula=f"net_income / total_equity = {ni} / {equity}"
        ) if roe is not None else _nd(f"roe.{lbl}", "Return on Equity", lbl, "missing net_income or equity"))

        roa = _safe_div(ni, assets)
        result.ratios.append(RatioResult(
            finding_id=f"roa.{lbl}", name="Return on Assets", period=lbl,
            value=_pct(roa), unit="%",
            formula=f"net_income / total_assets = {ni} / {assets}"
        ) if roa is not None else _nd(f"roa.{lbl}", "Return on Assets", lbl, "missing net_income or assets"))

        # ROCE = EBIT / Capital Employed (total_assets - current_liabilities)
        ce = (assets - cl) if (assets is not None and cl is not None) else None
        roce = _safe_div(ebit, ce)
        result.ratios.append(RatioResult(
            finding_id=f"roce.{lbl}", name="Return on Capital Employed", period=lbl,
            value=_pct(roce), unit="%",
            formula=f"ebit / (total_assets - current_liabilities) = {ebit} / ({assets} - {cl})"
        ) if roce is not None else _nd(f"roce.{lbl}", "ROCE", lbl, "missing ebit, assets, or current_liabilities"))

    # ── Liquidity ─────────────────────────────────────────────────────────────

    bs_periods = [p.label for p in bs.periods]
    for lbl in bs_periods:
        ca = bs.current_assets.get(lbl)
        cl = bs.current_liabilities.get(lbl)
        cash = bs.cash.get(lbl)
        inv = bs.inventory.get(lbl)

        current_ratio = _safe_div(ca, cl)
        result.ratios.append(RatioResult(
            finding_id=f"current_ratio.{lbl}", name="Current Ratio", period=lbl,
            value=current_ratio, unit="x",
            formula=f"current_assets / current_liabilities = {ca} / {cl}"
        ) if current_ratio is not None else _nd(f"current_ratio.{lbl}", "Current Ratio", lbl, "missing current_assets or current_liabilities"))

        quick = _safe_div((ca - inv) if (ca is not None and inv is not None) else None, cl)
        result.ratios.append(RatioResult(
            finding_id=f"quick_ratio.{lbl}", name="Quick Ratio", period=lbl,
            value=quick, unit="x",
            formula=f"(current_assets - inventory) / current_liabilities = ({ca} - {inv}) / {cl}"
        ) if quick is not None else _nd(f"quick_ratio.{lbl}", "Quick Ratio", lbl, "missing data"))

        cash_ratio = _safe_div(cash, cl)
        result.ratios.append(RatioResult(
            finding_id=f"cash_ratio.{lbl}", name="Cash Ratio", period=lbl,
            value=cash_ratio, unit="x",
            formula=f"cash / current_liabilities = {cash} / {cl}"
        ) if cash_ratio is not None else _nd(f"cash_ratio.{lbl}", "Cash Ratio", lbl, "missing cash or current_liabilities"))

    # ── Efficiency ────────────────────────────────────────────────────────────

    for lbl in periods:
        rev = is_.revenue.get(lbl)
        cogs = is_.cost_of_goods_sold.get(lbl)
        ar = bs.accounts_receivable.get(lbl)
        ap = bs.accounts_payable.get(lbl)
        inv = bs.inventory.get(lbl)
        assets = bs.total_assets.get(lbl)

        dso = _safe_div(ar, rev)
        dso_val = dso * 365 if dso is not None else None
        result.ratios.append(RatioResult(
            finding_id=f"dso.{lbl}", name="Days Sales Outstanding", period=lbl,
            value=dso_val, unit="days",
            formula=f"(accounts_receivable / revenue) * 365 = ({ar} / {rev}) * 365"
        ) if dso_val is not None else _nd(f"dso.{lbl}", "DSO", lbl, "missing accounts_receivable or revenue"))

        dpo = _safe_div(ap, cogs)
        dpo_val = dpo * 365 if dpo is not None else None
        result.ratios.append(RatioResult(
            finding_id=f"dpo.{lbl}", name="Days Payable Outstanding", period=lbl,
            value=dpo_val, unit="days",
            formula=f"(accounts_payable / cogs) * 365 = ({ap} / {cogs}) * 365"
        ) if dpo_val is not None else _nd(f"dpo.{lbl}", "DPO", lbl, "missing accounts_payable or cogs"))

        inv_days_raw = _safe_div(inv, cogs)
        inv_days = inv_days_raw * 365 if inv_days_raw is not None else None
        result.ratios.append(RatioResult(
            finding_id=f"inventory_days.{lbl}", name="Inventory Days", period=lbl,
            value=inv_days, unit="days",
            formula=f"(inventory / cogs) * 365 = ({inv} / {cogs}) * 365"
        ) if inv_days is not None else _nd(f"inventory_days.{lbl}", "Inventory Days", lbl, "missing inventory or cogs"))

        if dso_val is not None and inv_days is not None and dpo_val is not None:
            ccc = dso_val + inv_days - dpo_val
            result.ratios.append(RatioResult(
                finding_id=f"ccc.{lbl}", name="Cash Conversion Cycle", period=lbl,
                value=ccc, unit="days",
                formula=f"DSO + inventory_days - DPO = {dso_val:.1f} + {inv_days:.1f} - {dpo_val:.1f}"
            ))
        else:
            result.ratios.append(_nd(f"ccc.{lbl}", "Cash Conversion Cycle", lbl, "requires DSO, inventory_days, DPO"))

        at = _safe_div(rev, assets)
        result.ratios.append(RatioResult(
            finding_id=f"asset_turnover.{lbl}", name="Asset Turnover", period=lbl,
            value=at, unit="x",
            formula=f"revenue / total_assets = {rev} / {assets}"
        ) if at is not None else _nd(f"asset_turnover.{lbl}", "Asset Turnover", lbl, "missing revenue or assets"))

    # ── Leverage ──────────────────────────────────────────────────────────────

    for lbl in bs_periods:
        total_l = bs.total_liabilities.get(lbl)
        equity = bs.total_equity.get(lbl)
        ltd = bs.long_term_debt.get(lbl)
        std = bs.short_term_debt.get(lbl)
        cash = bs.cash.get(lbl)

        de = _safe_div(total_l, equity)
        result.ratios.append(RatioResult(
            finding_id=f"debt_to_equity.{lbl}", name="Debt to Equity", period=lbl,
            value=de, unit="x",
            formula=f"total_liabilities / total_equity = {total_l} / {equity}"
        ) if de is not None else _nd(f"debt_to_equity.{lbl}", "Debt to Equity", lbl, "missing data"))

    for lbl in periods:
        ebit = is_.ebit.get(lbl)
        ie = is_.interest_expense.get(lbl)
        da = is_.depreciation_amortization.get(lbl)
        ebitda_val = is_.ebitda.get(lbl)
        if ebitda_val is None and ebit is not None and da is not None:
            ebitda_val = ebit + da

        ic = _safe_div(ebit, ie)
        result.ratios.append(RatioResult(
            finding_id=f"interest_coverage.{lbl}", name="Interest Coverage", period=lbl,
            value=ic, unit="x",
            formula=f"ebit / interest_expense = {ebit} / {ie}"
        ) if ic is not None else _nd(f"interest_coverage.{lbl}", "Interest Coverage", lbl, "missing ebit or interest_expense"))

        # Net debt / EBITDA — cross-statement ratio; needs balance sheet for same period
        ltd = bs.long_term_debt.get(lbl)
        std = bs.short_term_debt.get(lbl)
        cash = bs.cash.get(lbl)
        if ltd is not None and std is not None and cash is not None and ebitda_val is not None:
            net_debt = ltd + std - cash
            nd_ebitda = _safe_div(net_debt, ebitda_val)
            result.ratios.append(RatioResult(
                finding_id=f"net_debt_ebitda.{lbl}", name="Net Debt / EBITDA", period=lbl,
                value=nd_ebitda, unit="x",
                formula=f"(long_term_debt + short_term_debt - cash) / ebitda = ({ltd} + {std} - {cash}) / {ebitda_val}"
            ))
        else:
            result.ratios.append(_nd(f"net_debt_ebitda.{lbl}", "Net Debt / EBITDA", lbl,
                                     "requires long_term_debt, short_term_debt, cash, ebitda"))

    # ── Growth ────────────────────────────────────────────────────────────────

    period_labels = [p.label for p in is_.periods]
    # YoY growth (needs at least 2 periods, sorted ascending)
    sorted_periods = sorted(period_labels)
    for i in range(1, len(sorted_periods)):
        curr, prev = sorted_periods[i], sorted_periods[i - 1]

        for metric, field_name in [("revenue", "revenue"), ("ebit", "ebit"), ("net_income", "net_income")]:
            curr_val = getattr(is_, field_name).get(curr)
            prev_val = getattr(is_, field_name).get(prev)
            growth = _safe_div(curr_val - prev_val if (curr_val is not None and prev_val is not None) else None, prev_val)
            rid = f"{metric}_growth_yoy.{curr}"
            if growth is not None:
                result.ratios.append(RatioResult(
                    finding_id=rid, name=f"{metric.capitalize()} YoY Growth", period=curr,
                    value=_pct(growth), unit="%",
                    formula=f"({curr_val} - {prev_val}) / {prev_val}"
                ))
            else:
                result.ratios.append(_nd(rid, f"{metric.capitalize()} YoY Growth", curr, "insufficient data"))

    # 3-year CAGR (needs at least 3 periods)
    if len(sorted_periods) >= 3:
        oldest, newest = sorted_periods[0], sorted_periods[-1]
        n_years = int(newest) - int(oldest)
        if n_years > 0:
            for metric, field_name in [("revenue", "revenue"), ("ebit", "ebit")]:
                v0 = getattr(is_, field_name).get(oldest)
                vn = getattr(is_, field_name).get(newest)
                rid = f"{metric}_cagr_{n_years}yr"
                if v0 and vn and v0 > 0:
                    cagr = ((vn / v0) ** (1 / n_years) - 1) * 100
                    result.ratios.append(RatioResult(
                        finding_id=rid, name=f"{metric.capitalize()} {n_years}yr CAGR", period=f"{oldest}-{newest}",
                        value=cagr, unit="%",
                        formula=f"(({vn} / {v0}) ^ (1/{n_years}) - 1) * 100"
                    ))
                else:
                    result.ratios.append(_nd(rid, f"{metric.capitalize()} CAGR", f"{oldest}-{newest}", "insufficient data"))

    return result
