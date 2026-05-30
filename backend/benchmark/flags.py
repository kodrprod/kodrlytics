"""Rule-based flagging engine. Compares computed ratios to benchmarks."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from backend.analysis.ratios import AnalysisResult
from backend.benchmark.store import BenchmarkStore


@dataclass
class BenchmarkFlag:
    finding_id: str                 # links to the RatioResult that triggered this
    flag_type: str                  # e.g. "receivables_slow", "liquidity_risk"
    severity: str                   # "warning" | "critical"
    metric: str
    period: str
    company_value: float
    peer_median: float
    peer_p25: float
    peer_p75: float
    delta_vs_median: float
    message: str
    quantified_impact: Optional[str] = None   # e.g. "~€1.2M capital tied up"


@dataclass
class BenchmarkResult:
    company_name: str
    nace_code: str
    flags: list[BenchmarkFlag] = field(default_factory=list)
    benchmarked_metrics: list[str] = field(default_factory=list)   # metrics that had peer data


def run_benchmark(analysis: AnalysisResult, nace_code: str,
                  store: BenchmarkStore) -> BenchmarkResult:
    result = BenchmarkResult(company_name=analysis.company_name, nace_code=nace_code)

    # Collect most recent period for each metric
    ratios_by_metric: dict[str, list] = {}
    for r in analysis.ratios:
        if not r.not_derivable and r.value is not None:
            ratios_by_metric.setdefault(r.name.lower().replace(" ", "_"), []).append(r)

    # Helper: get most recent ratio value for a metric by finding_id prefix
    def latest(prefix: str):
        matches = [r for r in analysis.ratios if r.finding_id.startswith(prefix) and not r.not_derivable]
        if not matches:
            return None
        return sorted(matches, key=lambda x: x.period)[-1]

    def flag(r, bm, flag_type: str, severity: str, message: str, impact: Optional[str] = None):
        result.flags.append(BenchmarkFlag(
            finding_id=r.finding_id, flag_type=flag_type, severity=severity,
            metric=r.finding_id.split(".")[0], period=r.period,
            company_value=r.value, peer_median=bm.median, peer_p25=bm.p25, peer_p75=bm.p75,
            delta_vs_median=r.value - bm.median, message=message,
            quantified_impact=impact
        ))

    # ── DSO: > peer_median * 1.3 → receivables slow ───────────────────────────
    dso_r = latest("dso.")
    dso_bm = store.get(nace_code, "dso")
    if dso_r and dso_bm:
        result.benchmarked_metrics.append("dso")
        if dso_r.value > dso_bm.median * 1.3:
            # Capital tied up estimate
            rev_r = latest("asset_turnover.")  # use for context only
            # find revenue for same period
            dso_period = dso_r.period
            severity = "critical" if dso_r.value > dso_bm.p75 * 1.5 else "warning"
            result.flags.append(BenchmarkFlag(
                finding_id=dso_r.finding_id, flag_type="receivables_slow", severity=severity,
                metric="dso", period=dso_period,
                company_value=dso_r.value, peer_median=dso_bm.median,
                peer_p25=dso_bm.p25, peer_p75=dso_bm.p75,
                delta_vs_median=dso_r.value - dso_bm.median,
                message=(f"DSO {dso_r.value:.0f} days vs peer median {dso_bm.median:.0f} days "
                         f"(+{dso_r.value - dso_bm.median:.0f} days). Receivables collection is slow."),
            ))

    # ── Current ratio < 1.0 → liquidity risk ─────────────────────────────────
    cr_r = latest("current_ratio.")
    cr_bm = store.get(nace_code, "current_ratio")
    if cr_r and cr_bm:
        result.benchmarked_metrics.append("current_ratio")
        if cr_r.value < 1.0:
            flag(cr_r, cr_bm, "liquidity_risk", "critical",
                 f"Current ratio {cr_r.value:.2f}x is below 1.0 — current liabilities exceed current assets.")
        elif cr_r.value < cr_bm.p25:
            flag(cr_r, cr_bm, "liquidity_below_peers", "warning",
                 f"Current ratio {cr_r.value:.2f}x is below peer 25th percentile ({cr_bm.p25:.2f}x).")

    # ── EBIT margin declining 2+ years ────────────────────────────────────────
    ebit_margins = sorted(
        [r for r in analysis.ratios if r.finding_id.startswith("ebit_margin.") and not r.not_derivable],
        key=lambda x: x.period
    )
    if len(ebit_margins) >= 3:
        values = [r.value for r in ebit_margins[-3:]]
        if values[0] > values[1] > values[2]:
            bm = store.get(nace_code, "ebit_margin")
            if bm:
                result.benchmarked_metrics.append("ebit_margin_trend")
                result.flags.append(BenchmarkFlag(
                    finding_id=ebit_margins[-1].finding_id,
                    flag_type="margin_erosion", severity="warning",
                    metric="ebit_margin", period=ebit_margins[-1].period,
                    company_value=ebit_margins[-1].value,
                    peer_median=bm.median, peer_p25=bm.p25, peer_p75=bm.p75,
                    delta_vs_median=ebit_margins[-1].value - bm.median,
                    message=(f"EBIT margin has declined for 3 consecutive years: "
                             f"{values[0]:.1f}% → {values[1]:.1f}% → {values[2]:.1f}%. "
                             f"Peer median: {bm.median:.1f}%."),
                ))

    # ── Gross margin below peer p25 ───────────────────────────────────────────
    gm_r = latest("gross_margin.")
    gm_bm = store.get(nace_code, "gross_margin")
    if gm_r and gm_bm:
        result.benchmarked_metrics.append("gross_margin")
        if gm_r.value < gm_bm.p25:
            flag(gm_r, gm_bm, "low_gross_margin", "warning",
                 f"Gross margin {gm_r.value:.1f}% is below peer 25th percentile ({gm_bm.p25:.1f}%).")

    # ── Leverage: D/E > peer p75 ──────────────────────────────────────────────
    de_r = latest("debt_to_equity.")
    de_bm = store.get(nace_code, "debt_to_equity")
    if de_r and de_bm:
        result.benchmarked_metrics.append("debt_to_equity")
        if de_r.value > de_bm.p75 * 1.2:
            flag(de_r, de_bm, "high_leverage", "warning",
                 f"D/E {de_r.value:.2f}x exceeds peer 75th percentile ({de_bm.p75:.2f}x).")

    # ── Interest coverage < 2x → debt service risk ───────────────────────────
    ic_r = latest("interest_coverage.")
    ic_bm = store.get(nace_code, "interest_coverage")
    if ic_r and ic_bm:
        result.benchmarked_metrics.append("interest_coverage")
        if ic_r.value < 2.0:
            sev = "critical" if ic_r.value < 1.0 else "warning"
            flag(ic_r, ic_bm, "debt_service_risk", sev,
                 f"Interest coverage {ic_r.value:.1f}x is {'dangerously' if sev == 'critical' else ''} low. "
                 f"Peer median: {ic_bm.median:.1f}x.")

    return result
