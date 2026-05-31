"""6-room multi-agent pipeline orchestrator."""
from __future__ import annotations
import dataclasses
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Awaitable

from backend.agents.models import PipelineContext
from backend.agents.rooms import (
    IntakeRoom, ExtractionRoom, AnalysisRoom,
    BenchmarkingRoom, StrategyRoom, ReportingRoom,
)

log = logging.getLogger(__name__)


async def run_room_pipeline(
    filename: str,
    content: bytes,
    run_id: str,
    emit: Callable[..., Awaitable[None]],
) -> None:
    """Run all 6 rooms in sequence, emitting events to the WebSocket."""
    ctx = PipelineContext(filename=filename, content=content)
    rooms = [
        IntakeRoom(), ExtractionRoom(), AnalysisRoom(),
        BenchmarkingRoom(), StrategyRoom(), ReportingRoom(),
    ]

    for room in rooms:
        try:
            await room.run(ctx, run_id, emit)
        except Exception as e:
            log.error("Room %s crashed: %s", room.name, e, exc_info=True)
            await emit({
                "event_type": "run_error", "run_id": run_id,
                "stage": room.name, "error": str(e),
            })

    # Emit run_complete so the HUD can display results
    try:
        ratios, flags, projections = [], [], []

        if ctx.analysis:
            for r in ctx.analysis.ratios:
                if not r.not_derivable and r.value is not None:
                    ratios.append(dataclasses.asdict(r))

        if ctx.benchmark:
            for f in ctx.benchmark.flags:
                flags.append({
                    "flag_type": f.flag_type, "severity": f.severity,
                    "message": f.message, "metric": f.metric,
                })

        if ctx.projections:
            for p in ctx.projections:
                projections.append({
                    "metric": p.metric,
                    "current_value": p.current_value,
                    "unit": p.action.unit,
                    "description": p.action.description,
                    "disclaimer": p.disclaimer,
                    "scenarios": [
                        {"label": s.label, "target_value": s.target_value,
                         "impact_eur": s.impact_eur, "impact_description": s.impact_description}
                        for s in p.scenarios
                    ],
                })

        narrative = ctx.room_reports.get("Reporting", "")
        company_name = getattr(ctx.financials, "company_name", "Unknown") if ctx.financials else "Unknown"

        await emit({
            "event_type": "run_complete", "run_id": run_id,
            "company_name": company_name,
            "total_duration_ms": 0,
            "finding_count": len(ratios),
            "flag_count": len(flags),
            "ratios": ratios,
            "flags": flags,
            "projections": projections,
            "narrative": narrative,
        })
    except Exception as e:
        log.error("run_complete emission failed: %s", e)
        await emit({"event_type": "run_error", "run_id": run_id, "stage": "reporting", "error": str(e)})
