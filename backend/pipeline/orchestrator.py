"""Pipeline orchestrator. Runs all 5 stages and yields PipelineEvent objects."""
from __future__ import annotations
import asyncio
import dataclasses
import json
import time
import uuid
import logging
from pathlib import Path
from typing import AsyncGenerator

from backend.pipeline.events import (
    StageStartedEvent, DataPassedEvent, FindingCreatedEvent,
    FlagRaisedEvent, StageDoneEvent, RunErrorEvent, RunCompleteEvent,
    PipelineEvent,
)
from backend.schema.models import CompanyFinancials
from backend.analysis.ratios import run_analysis
from backend.analysis.reconciliation import reconcile
from backend.benchmark.store import BenchmarkStore
from backend.benchmark.flags import run_benchmark
from backend.intake.extractor import extract_financials
from backend.strategy.actions import build_actions_from_flags
from backend.strategy.projections import compute_projections, format_projections_summary
from backend.briefing.narrator import generate_briefing

logger = logging.getLogger(__name__)

STAGES = ["intake", "analysis", "benchmark", "strategy", "briefing"]
BENCHMARK_DIR = Path(__file__).parent.parent.parent / "data" / "benchmarks"


async def run_pipeline(
    filename: str,
    content: bytes,
    run_id: str = None,
) -> AsyncGenerator[PipelineEvent, None]:
    """
    Async generator that runs the full 5-stage pipeline and yields events.
    Usage:
        async for event in run_pipeline(filename, content):
            await ws.send_json(event.model_dump())
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    run_start = time.monotonic()

    # ── Stage 0: Intake ───────────────────────────────────────────────────────
    stage = "intake"
    t0 = time.monotonic()
    yield StageStartedEvent(run_id=run_id, stage=stage, stage_index=0)

    try:
        extraction = await extract_financials(filename, content)
        financials = extraction.financials
        recon = extraction.reconciliation
        if not recon.passed:
            errors_str = "; ".join(f"{e.check} (period {e.period})" for e in recon.errors)
            yield RunErrorEvent(run_id=run_id, stage=stage,
                                error=f"Reconciliation gate failed: {errors_str}")
            return
    except Exception as e:
        yield RunErrorEvent(run_id=run_id, stage=stage, error=str(e))
        return

    yield StageDoneEvent(run_id=run_id, stage=stage, stage_index=0,
                         duration_ms=int((time.monotonic() - t0) * 1000))

    n_periods = len(financials.income_statement.periods)
    yield DataPassedEvent(run_id=run_id, from_stage="intake", to_stage="analysis",
                          summary=f"{financials.company_name}: {n_periods} year(s) of financials extracted and reconciled")

    # ── Stage 1: Analysis ─────────────────────────────────────────────────────
    stage = "analysis"
    t0 = time.monotonic()
    yield StageStartedEvent(run_id=run_id, stage=stage, stage_index=1)

    try:
        analysis = run_analysis(financials)
    except Exception as e:
        yield RunErrorEvent(run_id=run_id, stage=stage, error=str(e))
        return

    # Emit key findings (emit first 8 most important ratios to avoid flooding)
    KEY_RATIOS = ["gross_margin", "ebit_margin", "net_margin", "roe",
                  "current_ratio", "dso", "debt_to_equity", "interest_coverage"]
    latest_period = sorted(financials.income_statement.periods, key=lambda p: p.year)[-1].label
    for prefix in KEY_RATIOS:
        r = analysis.by_id(f"{prefix}.{latest_period}")
        if r and not r.not_derivable:
            yield FindingCreatedEvent(
                run_id=run_id, stage=stage,
                finding_id=r.finding_id, name=r.name,
                value=round(r.value, 2) if r.value is not None else None,
                unit=r.unit, period=r.period,
            )
            await asyncio.sleep(0.05)  # small delay so frontend animates each label

    yield StageDoneEvent(run_id=run_id, stage=stage, stage_index=1,
                         duration_ms=int((time.monotonic() - t0) * 1000))
    yield DataPassedEvent(run_id=run_id, from_stage="analysis", to_stage="benchmark",
                          summary=f"{len(analysis.ratios)} ratios computed")

    # ── Stage 2: Benchmark ────────────────────────────────────────────────────
    stage = "benchmark"
    t0 = time.monotonic()
    yield StageStartedEvent(run_id=run_id, stage=stage, stage_index=2)

    try:
        store = BenchmarkStore(data_dir=BENCHMARK_DIR)
        benchmark = run_benchmark(analysis, financials.nace_code, store)
    except Exception as e:
        yield RunErrorEvent(run_id=run_id, stage=stage, error=str(e))
        return

    for flag in benchmark.flags:
        yield FlagRaisedEvent(
            run_id=run_id, stage=stage,
            flag_type=flag.flag_type, severity=flag.severity,
            message=flag.message, metric=flag.metric,
        )
        await asyncio.sleep(0.08)

    yield StageDoneEvent(run_id=run_id, stage=stage, stage_index=2,
                         duration_ms=int((time.monotonic() - t0) * 1000))
    yield DataPassedEvent(run_id=run_id, from_stage="benchmark", to_stage="strategy",
                          summary=f"{len(benchmark.flags)} flag(s) raised vs {len(benchmark.benchmarked_metrics)} peer metrics")

    # ── Stage 3: Strategy ─────────────────────────────────────────────────────
    stage = "strategy"
    t0 = time.monotonic()
    yield StageStartedEvent(run_id=run_id, stage=stage, stage_index=3)

    try:
        actions = build_actions_from_flags(benchmark.flags, store, financials.nace_code)
        projections = compute_projections(actions, financials)
        proj_summary = format_projections_summary(projections)
    except Exception as e:
        yield RunErrorEvent(run_id=run_id, stage=stage, error=str(e))
        return

    yield StageDoneEvent(run_id=run_id, stage=stage, stage_index=3,
                         duration_ms=int((time.monotonic() - t0) * 1000))
    yield DataPassedEvent(run_id=run_id, from_stage="strategy", to_stage="briefing",
                          summary=f"{len(projections)} projection(s) computed (conservative/base/optimistic)")

    # ── Stage 4: Briefing ─────────────────────────────────────────────────────
    stage = "briefing"
    t0 = time.monotonic()
    yield StageStartedEvent(run_id=run_id, stage=stage, stage_index=4)

    try:
        narrative, _grounding_passed = await generate_briefing(analysis, benchmark)
    except Exception as e:
        yield RunErrorEvent(run_id=run_id, stage=stage, error=str(e))
        return

    yield StageDoneEvent(run_id=run_id, stage=stage, stage_index=4,
                         duration_ms=int((time.monotonic() - t0) * 1000))

    # ── Run complete ──────────────────────────────────────────────────────────
    yield RunCompleteEvent(
        run_id=run_id,
        company_name=financials.company_name,
        total_duration_ms=int((time.monotonic() - run_start) * 1000),
        finding_count=len([r for r in analysis.ratios if not r.not_derivable]),
        flag_count=len(benchmark.flags),
        ratios=[dataclasses.asdict(r) for r in analysis.ratios if not r.not_derivable],
        flags=[dataclasses.asdict(f) for f in benchmark.flags],
        projections=[{
            "metric": p.metric,
            "current_value": p.current_value,
            "unit": p.action.unit,
            "description": p.action.description,
            "disclaimer": p.disclaimer,
            "scenarios": [dataclasses.asdict(s) for s in p.scenarios],
        } for p in projections],
        narrative=narrative,
    )
