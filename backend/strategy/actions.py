"""Typed improvement actions. Each action references a specific finding."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    REDUCE_DSO = "reduce_dso"
    IMPROVE_EBIT_MARGIN = "improve_ebit_margin"
    REDUCE_INVENTORY_DAYS = "reduce_inventory_days"
    REDUCE_LEVERAGE = "reduce_leverage"
    IMPROVE_GROSS_MARGIN = "improve_gross_margin"


@dataclass
class ImprovementAction:
    action_type: ActionType
    finding_id: str                    # links to the RatioResult that motivated this
    current_value: float               # in the metric's native unit
    target_base: float                 # peer median (base scenario)
    target_optimistic: float           # peer p75 / best-quartile (optimistic)
    target_conservative: float         # halfway between current and median (conservative)
    unit: str
    assumptions: list[str] = field(default_factory=list)
    description: str = ""


def build_actions_from_flags(
    flags,  # list[BenchmarkFlag]
    store,  # BenchmarkStore
    nace_code: str,
) -> list[ImprovementAction]:
    """Create typed actions from benchmark flags using p25/p75 as scenario bounds."""
    actions = []
    for flag in flags:
        bm = store.get(nace_code, flag.metric)
        if bm is None:
            continue

        company_val = flag.company_value
        median = bm.median
        p75 = bm.p75
        p25 = bm.p25

        if flag.flag_type == "receivables_slow":
            conservative = company_val + (median - company_val) * 0.5  # halfway to median
            actions.append(ImprovementAction(
                action_type=ActionType.REDUCE_DSO,
                finding_id=flag.finding_id,
                current_value=company_val,
                target_base=median,
                target_optimistic=p25,    # fewer days = better, p25 is better for DSO
                target_conservative=conservative,
                unit="days",
                description=f"Reduce DSO from {company_val:.0f} to {median:.0f} days (peer median)",
                assumptions=[
                    f"Peer median DSO: {median:.0f} days (source: {bm.source})",
                    f"Peer best-quartile DSO: {p25:.0f} days",
                    "Assumes no change in revenue or customer mix",
                    "Cash freed = (current_dso - target_dso) / 365 × annual_revenue",
                    "Projection is illustrative; actual results depend on collection strategy execution",
                ],
            ))

        elif flag.flag_type in ("margin_erosion", "low_gross_margin"):
            conservative = company_val + (median - company_val) * 0.5
            actions.append(ImprovementAction(
                action_type=ActionType.IMPROVE_EBIT_MARGIN,
                finding_id=flag.finding_id,
                current_value=company_val,
                target_base=median,
                target_optimistic=p75,
                target_conservative=conservative,
                unit="%",
                description=f"Improve EBIT margin from {company_val:.1f}% to {median:.1f}% (peer median)",
                assumptions=[
                    f"Peer median EBIT margin: {median:.1f}% (source: {bm.source})",
                    f"Peer top-quartile EBIT margin: {p75:.1f}%",
                    "Assumes revenue held constant; improvement via cost reduction",
                    "Projection is illustrative; not a guarantee",
                ],
            ))

        elif flag.flag_type == "high_leverage":
            conservative = company_val - (company_val - median) * 0.5
            actions.append(ImprovementAction(
                action_type=ActionType.REDUCE_LEVERAGE,
                finding_id=flag.finding_id,
                current_value=company_val,
                target_base=median,
                target_optimistic=p25,
                target_conservative=conservative,
                unit="x",
                description=f"Reduce D/E from {company_val:.2f}x to {median:.2f}x (peer median)",
                assumptions=[
                    f"Peer median D/E: {median:.2f}x (source: {bm.source})",
                    "Assumes debt repayment funded by operating cash flow",
                    "Projection is illustrative; not a guarantee",
                ],
            ))

    return actions
