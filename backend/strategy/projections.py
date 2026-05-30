"""Deterministic projection engine. The LLM proposes actions; this code computes outcomes.
All numbers are derived from formulae — no LLM involvement here.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from backend.strategy.actions import ImprovementAction, ActionType
from backend.schema.models import CompanyFinancials


@dataclass
class Scenario:
    label: str           # "conservative" | "base" | "optimistic"
    target_value: float
    impact_eur: Optional[float]     # monetary impact in EUR (None if not computable)
    impact_description: str
    assumptions_used: list[str] = field(default_factory=list)


@dataclass
class ProjectionResult:
    action: ImprovementAction
    metric: str
    current_value: float
    scenarios: list[Scenario]
    disclaimer: str = "This is a projection, not a guarantee. All scenarios assume partial or full implementation of the stated action under stable business conditions."

    def as_dict(self) -> dict[str, float]:
        """For grounding gate: expose all projected numbers."""
        result = {}
        for s in self.scenarios:
            result[f"projection.{self.metric}.{s.label}.target"] = s.target_value
            if s.impact_eur is not None:
                result[f"projection.{self.metric}.{s.label}.impact_eur"] = s.impact_eur
        return result


def _project_dso(action: ImprovementAction, financials: CompanyFinancials) -> list[Scenario]:
    """DSO reduction: freed cash = (current - target) / 365 * revenue."""
    is_ = financials.income_statement
    latest_period = sorted(is_.periods, key=lambda p: p.year)[-1].label
    revenue = is_.revenue.get(latest_period, 0)

    scenarios = []
    for label, target in [
        ("conservative", action.target_conservative),
        ("base", action.target_base),
        ("optimistic", action.target_optimistic),
    ]:
        freed_cash = (action.current_value - target) / 365 * revenue
        scenarios.append(Scenario(
            label=label,
            target_value=round(target, 1),
            impact_eur=round(freed_cash, 0),
            impact_description=(
                f"DSO {action.current_value:.0f} → {target:.0f} days frees "
                f"€{freed_cash:,.0f} in working capital"
            ),
            assumptions_used=action.assumptions,
        ))
    return scenarios


def _project_ebit_margin(action: ImprovementAction, financials: CompanyFinancials) -> list[Scenario]:
    """EBIT margin improvement: impact = (target_margin - current_margin) / 100 * revenue."""
    is_ = financials.income_statement
    latest_period = sorted(is_.periods, key=lambda p: p.year)[-1].label
    revenue = is_.revenue.get(latest_period, 0)

    scenarios = []
    for label, target in [
        ("conservative", action.target_conservative),
        ("base", action.target_base),
        ("optimistic", action.target_optimistic),
    ]:
        ebit_delta = (target - action.current_value) / 100 * revenue
        scenarios.append(Scenario(
            label=label,
            target_value=round(target, 2),
            impact_eur=round(ebit_delta, 0),
            impact_description=(
                f"EBIT margin {action.current_value:.1f}% → {target:.1f}% adds "
                f"€{ebit_delta:,.0f} EBIT"
            ),
            assumptions_used=action.assumptions,
        ))
    return scenarios


def _project_leverage(action: ImprovementAction, financials: CompanyFinancials) -> list[Scenario]:
    """D/E reduction: qualitative (no simple single-number impact)."""
    scenarios = []
    for label, target in [
        ("conservative", action.target_conservative),
        ("base", action.target_base),
        ("optimistic", action.target_optimistic),
    ]:
        scenarios.append(Scenario(
            label=label,
            target_value=round(target, 2),
            impact_eur=None,
            impact_description=f"D/E {action.current_value:.2f}x → {target:.2f}x",
            assumptions_used=action.assumptions,
        ))
    return scenarios


_PROJECTORS = {
    ActionType.REDUCE_DSO: _project_dso,
    ActionType.IMPROVE_EBIT_MARGIN: _project_ebit_margin,
    ActionType.REDUCE_LEVERAGE: _project_leverage,
    ActionType.IMPROVE_GROSS_MARGIN: _project_ebit_margin,  # same formula
    ActionType.REDUCE_INVENTORY_DAYS: _project_dso,          # same formula (COGS-based)
}


def compute_projections(
    actions: list[ImprovementAction],
    financials: CompanyFinancials,
) -> list[ProjectionResult]:
    results = []
    for action in actions:
        projector = _PROJECTORS.get(action.action_type)
        if projector is None:
            continue
        scenarios = projector(action, financials)
        results.append(ProjectionResult(
            action=action,
            metric=action.action_type.value,
            current_value=action.current_value,
            scenarios=scenarios,
        ))
    return results


def format_projections_summary(projections: list[ProjectionResult]) -> str:
    """Format projections into a plain-text summary for the narrative prompt."""
    if not projections:
        return "No projections computed."
    lines = []
    for p in projections:
        lines.append(f"\n{p.action.description} (current: {p.current_value:.2f} {p.action.unit})")
        for s in p.scenarios:
            eur = f" | €{s.impact_eur:,.0f} impact" if s.impact_eur is not None else ""
            lines.append(f"  {s.label:>12}: target={s.target_value:.2f} {p.action.unit}{eur}")
        lines.append(f"  Disclaimer: {p.disclaimer}")
    return "\n".join(lines)
