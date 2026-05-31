"""
Single source of truth for all computed facts.

Every number that appears in a report MUST trace back to a Fact in this store.
LLMs reference Fact ids — they cannot introduce new numbers.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class FactKind(str, Enum):
    sourced = "sourced"   # value read directly from source data
    derived = "derived"   # computed deterministically from sourced facts
    gap     = "gap"       # data not available in source


@dataclass
class Fact:
    id: str
    label: str
    value: Optional[float]
    unit: str
    period: str
    source_ref: str      # file/row path or formula string
    kind: FactKind


class FactsStore:
    """Registry of all verified facts for a single pipeline run."""

    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}

    # ── Write ────────────────────────────────────────────────────────────────

    def add(self, fact: Fact) -> None:
        self._facts[fact.id] = fact

    # ── Read ─────────────────────────────────────────────────────────────────

    def get(self, id: str) -> Optional[Fact]:
        return self._facts.get(id)

    def format(self, id: str) -> str:
        """Return a human-readable string for a fact, or a [gap] placeholder."""
        fact = self.get(id)
        if fact is None or fact.kind == FactKind.gap or fact.value is None:
            return "[gap — data not available]"
        v = fact.value
        u = fact.unit
        if u == "%":
            return f"{v:.1f}%"
        if u in ("EUR", "€"):
            if abs(v) >= 1_000_000:
                return f"EUR {v / 1_000_000:.2f}M"
            if abs(v) >= 1_000:
                return f"EUR {v / 1_000:.1f}k"
            return f"EUR {v:,.2f}"
        if u in ("x", "times"):
            return f"{v:.2f}x"
        if u == "days":
            return f"{v:.0f} days"
        if u:
            return f"{v:.2f} {u}"
        return f"{v:.2f}"

    def all_values(self) -> dict[str, float]:
        """Return {id: value} for all non-gap facts — used by the grounding gate."""
        return {
            fid: f.value
            for fid, f in self._facts.items()
            if f.value is not None and f.kind != FactKind.gap
        }

    def render_tables(self) -> str:
        """Render a facts table for injection into worker/manager prompts."""
        if not self._facts:
            return "(No verified facts computed yet.)"
        lines: list[str] = ["VERIFIED FACTS — reference these ids; do not introduce other numbers:"]
        periods = sorted({f.period for f in self._facts.values() if f.period and f.period != "projected"})
        # Non-period facts first
        for fid, f in sorted(self._facts.items()):
            if f.period not in periods:
                tag = f"[{f.kind.value}]"
                val_str = self.format(fid) if f.kind != FactKind.gap else "[gap]"
                lines.append(f"  {fid:<55} {val_str:<22} {f.label} {tag}")
        # Then by period
        for period in periods:
            lines.append(f"\n  --- {period} ---")
            for fid, f in sorted(self._facts.items()):
                if f.period != period:
                    continue
                tag = f"[{f.kind.value}]"
                val_str = self.format(fid) if f.kind != FactKind.gap else "[gap]"
                lines.append(f"  {fid:<55} {val_str:<22} {f.label} {tag}")
        return "\n".join(lines)


def build_facts_store(
    analysis=None,      # AnalysisResult | None
    benchmark=None,     # BenchmarkResult | None
    projections=None,   # list[ProjectionResult] | None
    financials=None,    # CompanyFinancials | None
) -> FactsStore:
    """Populate a FactsStore from all deterministic pipeline outputs."""
    store = FactsStore()

    # ── Raw financial values from income statement / balance sheet ────────────
    if financials:
        is_ = financials.income_statement
        bs  = financials.balance_sheet
        for lbl in [p.label for p in is_.periods]:
            for fname in (
                "revenue", "cost_of_goods_sold", "gross_profit",
                "operating_expenses", "ebit", "interest_expense",
                "ebt", "income_tax", "net_income",
                "depreciation_amortization", "ebitda",
            ):
                val = getattr(is_, fname, {}).get(lbl)
                if val is not None and val != 0.0:
                    store.add(Fact(
                        id=f"raw.{fname}.{lbl}",
                        label=f"{fname.replace('_',' ').title()} ({lbl})",
                        value=float(val),
                        unit="EUR",
                        period=lbl,
                        source_ref=f"income_statement.{fname}[{lbl}]",
                        kind=FactKind.sourced,
                    ))
        bs_lbls = [p.label for p in bs.periods]
        for lbl in bs_lbls:
            for fname in (
                "cash", "accounts_receivable", "inventory", "current_assets",
                "fixed_assets", "total_assets", "accounts_payable",
                "short_term_debt", "current_liabilities", "long_term_debt",
                "total_liabilities", "total_equity",
            ):
                val = getattr(bs, fname, {}).get(lbl)
                if val is not None and val != 0.0:
                    store.add(Fact(
                        id=f"raw.bs.{fname}.{lbl}",
                        label=f"{fname.replace('_',' ').title()} BS ({lbl})",
                        value=float(val),
                        unit="EUR",
                        period=lbl,
                        source_ref=f"balance_sheet.{fname}[{lbl}]",
                        kind=FactKind.sourced,
                    ))

    # ── Computed ratios ───────────────────────────────────────────────────────
    if analysis:
        for r in analysis.ratios:
            kind = FactKind.gap if r.not_derivable else FactKind.derived
            store.add(Fact(
                id=r.finding_id,
                label=r.name,
                value=r.value,
                unit=r.unit,
                period=r.period,
                source_ref=r.formula,
                kind=kind,
            ))
        # raw_values dict (from ratios module)
        for key, val in analysis.raw_values.items():
            if key not in store._facts:
                parts = key.split(".")
                period = parts[-1] if len(parts) >= 2 else ""
                store.add(Fact(
                    id=key, label=key.replace(".", " "),
                    value=float(val), unit="EUR",
                    period=period, source_ref=key,
                    kind=FactKind.sourced,
                ))

    # ── Benchmark flags ───────────────────────────────────────────────────────
    if benchmark:
        for f in benchmark.flags:
            store.add(Fact(
                id=f"flag.{f.finding_id}.company",
                label=f"{f.metric} — company value",
                value=f.company_value,
                unit="",
                period=f.period,
                source_ref=f.finding_id,
                kind=FactKind.derived,
            ))
            store.add(Fact(
                id=f"flag.{f.finding_id}.median",
                label=f"{f.metric} — peer median",
                value=f.peer_median,
                unit="",
                period=f.period,
                source_ref="benchmark_store",
                kind=FactKind.sourced,
            ))

    # ── Projections ───────────────────────────────────────────────────────────
    if projections:
        for p in projections:
            for s in p.scenarios:
                unit = getattr(p.action, "unit", "") if p.action else ""
                store.add(Fact(
                    id=f"projection.{p.metric}.{s.label}.target",
                    label=f"{p.metric} target ({s.label})",
                    value=s.target_value,
                    unit=unit,
                    period="projected",
                    source_ref="projection_formula",
                    kind=FactKind.derived,
                ))
                if s.impact_eur is not None:
                    store.add(Fact(
                        id=f"projection.{p.metric}.{s.label}.impact_eur",
                        label=f"{p.metric} EUR impact ({s.label})",
                        value=s.impact_eur,
                        unit="EUR",
                        period="projected",
                        source_ref="projection_formula",
                        kind=FactKind.derived,
                    ))

    log.info(
        "FactsStore built: %d facts (%d sourced, %d derived, %d gaps)",
        len(store._facts),
        sum(1 for f in store._facts.values() if f.kind == FactKind.sourced),
        sum(1 for f in store._facts.values() if f.kind == FactKind.derived),
        sum(1 for f in store._facts.values() if f.kind == FactKind.gap),
    )
    return store
