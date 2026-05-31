"""6-room multi-agent pipeline orchestrator with CEO layer and ZIP ingestion."""
from __future__ import annotations
import dataclasses
import logging
from typing import Callable, Awaitable

from backend.agents.models import PipelineContext
from backend.agents.rooms import (
    IntakeRoom, ExtractionRoom, AnalysisRoom,
    BenchmarkingRoom, StrategyRoom, ReportingRoom,
)

log = logging.getLogger(__name__)

ROOM_NAMES = ['Intake', 'Extraction', 'Analysis', 'Benchmarking', 'Strategy', 'Reporting']


async def run_room_pipeline(
    filename: str,
    content: bytes,
    run_id: str,
    emit: Callable[..., Awaitable[None]],
) -> None:
    """Full pipeline: ZIP ingestion → CEO planning → 6 rooms → CEO synthesis."""
    ctx = PipelineContext(filename=filename, content=content)

    # ── ZIP ingestion ──────────────────────────────────────────────────────────
    if filename.lower().endswith('.zip'):
        try:
            from backend.intake.zip_ingester import ingest_zip
            log.info("Pipeline: ingesting ZIP %s", filename)
            await emit({"event_type": "ceo_thinking", "run_id": run_id,
                        "message": f"Ingesting {filename}..."})
            ctx.dataset = ingest_zip(filename, content)
            log.info("Pipeline: ZIP ingested — %d files, %s",
                     ctx.dataset.total_files, ctx.dataset.company_name)
        except Exception as e:
            log.error("Pipeline: ZIP ingestion failed: %s", e)

    # ── CEO planning ───────────────────────────────────────────────────────────
    try:
        from backend.agents.ceo import CEO
        ceo = CEO()
        await emit({"event_type": "ceo_thinking", "run_id": run_id,
                    "message": "CEO reviewing dataset and planning analysis..."})
        dataset = ctx.dataset
        if dataset:
            ctx.room_briefs = await ceo.plan_and_brief(dataset, ROOM_NAMES)
            ctx.ceo_plan = ctx.room_briefs.get("__plan__", "")
            log.info("Pipeline: CEO plan generated, briefs for %d rooms", len(ctx.room_briefs))
        await emit({"event_type": "ceo_briefed", "run_id": run_id,
                    "message": "CEO has briefed all department managers."})
    except Exception as e:
        log.warning("Pipeline: CEO planning failed: %s", e)

    # ── 6 rooms ────────────────────────────────────────────────────────────────
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

    # ── CEO final synthesis ────────────────────────────────────────────────────
    try:
        from backend.agents.ceo import CEO
        ceo = CEO()
        await emit({"event_type": "ceo_thinking", "run_id": run_id,
                    "message": "CEO writing final executive synthesis..."})
        if ctx.dataset:
            ceo_summary = await ceo.final_synthesis(ctx.room_reports, ctx.dataset)
            ctx.room_reports["CEO"] = ceo_summary
        await emit({"event_type": "ceo_done", "run_id": run_id,
                    "message": "CEO synthesis complete."})
    except Exception as e:
        log.warning("Pipeline: CEO synthesis failed: %s", e)

    # ── Generate downloadable reports ─────────────────────────────────────────
    _pdf_url: str | None = None
    _docx_url: str | None = None
    try:
        from backend.reporting.pdf_generator import generate_rooms_pdf
        from backend.reporting.docx_generator import generate_rooms_docx
        _cn = ""
        if ctx.financials:
            _cn = getattr(ctx.financials, "company_name", "")
        if not _cn and ctx.dataset:
            _cn = ctx.dataset.company_name
        _cn = _cn or "Company"
        generate_rooms_pdf(ctx.room_reports, _cn, filename, run_id)
        generate_rooms_docx(ctx.room_reports, _cn, filename, run_id)
        _pdf_url = f"/reports/{run_id}.pdf"
        _docx_url = f"/reports/{run_id}.docx"
        log.info("Pipeline: reports generated for %s", run_id)
    except Exception as e:
        log.warning("Pipeline: report generation failed: %s", e)

    # ── run_complete ───────────────────────────────────────────────────────────
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

        narrative = ctx.room_reports.get("CEO") or ctx.room_reports.get("Reporting", "")
        company_name = ""
        if ctx.financials:
            company_name = getattr(ctx.financials, "company_name", "")
        if not company_name and ctx.dataset:
            company_name = ctx.dataset.company_name
        if not company_name:
            company_name = "Unknown"

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
            "pdf_url": _pdf_url,
            "docx_url": _docx_url,
        })
    except Exception as e:
        log.error("run_complete emission failed: %s", e)
        await emit({"event_type": "run_error", "run_id": run_id,
                    "stage": "reporting", "error": str(e)})
