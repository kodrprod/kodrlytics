"""Tests for the deterministic projection engine (no LLM)."""
import pytest
from backend.schema.models import CompanyFinancials
from backend.strategy.actions import ImprovementAction, ActionType
from backend.strategy.projections import compute_projections, format_projections_summary


def _sample_financials() -> CompanyFinancials:
    return CompanyFinancials(**{
        "company_name": "Proj Test GmbH",
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


def _dso_action() -> ImprovementAction:
    return ImprovementAction(
        action_type=ActionType.REDUCE_DSO,
        finding_id="dso.2023",
        current_value=77.9,
        target_base=48.0,        # peer median
        target_optimistic=32.0,  # peer p25 (fewer days = better)
        target_conservative=62.9, # halfway to median
        unit="days",
        assumptions=["Peer median DSO: 48 days", "Projection, not a guarantee"],
        description="Reduce DSO to peer median",
    )


def test_dso_projection_base():
    fin = _sample_financials()
    action = _dso_action()
    results = compute_projections([action], fin)
    assert len(results) == 1
    proj = results[0]
    base = next(s for s in proj.scenarios if s.label == "base")
    # freed_cash = (77.9 - 48.0) / 365 * 9,800,000
    expected = (77.9 - 48.0) / 365 * 9_800_000
    assert abs(base.impact_eur - expected) < 1.0
    assert base.target_value == 48.0


def test_dso_projection_three_scenarios():
    fin = _sample_financials()
    action = _dso_action()
    results = compute_projections([action], fin)
    proj = results[0]
    assert {s.label for s in proj.scenarios} == {"conservative", "base", "optimistic"}


def test_dso_conservative_less_than_base():
    fin = _sample_financials()
    action = _dso_action()
    results = compute_projections([action], fin)
    proj = results[0]
    cons = next(s for s in proj.scenarios if s.label == "conservative")
    base = next(s for s in proj.scenarios if s.label == "base")
    # conservative frees less cash than base
    assert cons.impact_eur < base.impact_eur


def test_projection_as_dict_for_grounding():
    fin = _sample_financials()
    action = _dso_action()
    results = compute_projections([action], fin)
    d = results[0].as_dict()
    assert "projection.reduce_dso.base.target" in d
    assert "projection.reduce_dso.base.impact_eur" in d


def test_format_projections_summary():
    fin = _sample_financials()
    action = _dso_action()
    results = compute_projections([action], fin)
    summary = format_projections_summary(results)
    assert "conservative" in summary
    assert "base" in summary
    assert "optimistic" in summary
    assert "projection, not a guarantee" in summary.lower()


def test_ebit_margin_projection():
    fin = _sample_financials()
    action = ImprovementAction(
        action_type=ActionType.IMPROVE_EBIT_MARGIN,
        finding_id="ebit_margin.2023",
        current_value=18.0,
        target_base=5.8,
        target_optimistic=9.7,
        target_conservative=11.9,
        unit="%",
        assumptions=["Peer median 5.8%"],
        description="Improve EBIT margin",
    )
    results = compute_projections([action], fin)
    proj = results[0]
    base = next(s for s in proj.scenarios if s.label == "base")
    # target 5.8% vs current 18.0% — this actually shows a DECLINE, which is unusual but tests formula
    expected = (5.8 - 18.0) / 100 * 9_800_000
    assert abs(base.impact_eur - expected) < 1.0
