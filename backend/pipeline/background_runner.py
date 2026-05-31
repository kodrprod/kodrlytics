"""Background pipeline runner for long-running jobs."""
from __future__ import annotations
import asyncio
import json
import logging
import time
from pathlib import Path

from backend.intake.zip_processor import extract_zip, CompanyBatch
from backend.intake.extractor import extract_financials
from backend.intake.parsers import parse_document
from backend.analysis.ratios import run_analysis
from backend.analysis.reconciliation import reconcile
from backend.benchmark.store import BenchmarkStore
from backend.benchmark.flags import run_benchmark
from backend.strategy.actions import build_actions_from_flags
from backend.strategy.projections import compute_projections, format_projections_summary
from backend.briefing.narrator import generate_briefing
from backend.reporting.deep_narrator import generate_deep_recommendations
from backend.reporting.pdf_generator import generate_pdf, AnalysisReport, CompanyReport
from backend.pipeline.job_store import update_job, append_event

log = logging.getLogger(__name__)

BENCHMARK_DIR = Path(__file__).parent.parent.parent / "data" / "benchmarks"


def _evt(job_id: str, event_type: str, **kwargs):
    event = {"event_type": event_type, "ts": time.time(), **kwargs}
    append_event(job_id, event)
    return event


async def _process_company_batch(
    batch: CompanyBatch,
    store: BenchmarkStore,
    job_id: str,
) -> CompanyReport | None:
    """Process one company batch (one or more files). Returns a CompanyReport or None on failure."""
    log.info("Job %s: processing company '%s' (%d files)", job_id, batch.company_hint, len(batch.files))

    # Merge all files in the batch into one extraction attempt
    # Strategy: try each file until extraction succeeds
    financials = None
    recon = None
    for filename, content in batch.files:
        try:
            result = await extract_financials(filename, content, company_hint=batch.company_hint)
            if result.reconciliation.passed:
                financials = result.financials
                recon = result.reconciliation
                log.info("Job %s: extracted '%s' from %s", job_id, financials.company_name, filename)
                break
            elif financials is None:
                financials = result.financials
                recon = result.reconciliation
        except Exception as e:
            log.warning("Job %s: failed to extract %s: %s", job_id, filename, e)
            continue

    if financials is None:
        _evt(job_id, "company_error", company=batch.company_hint, error="All files failed extraction")
        return None

    _evt(job_id, "company_extracted", company=financials.company_name,
         periods=len(financials.income_statement.periods))

    # Analysis
    analysis = run_analysis(financials)
    benchmark = run_benchmark(analysis, financials.nace_code, store)
    _evt(job_id, "company_analysed", company=financials.company_name,
         ratio_count=len([r for r in analysis.ratios if not r.not_derivable]),
         flag_count=len(benchmark.flags))

    # Strategy
    actions = build_actions_from_flags(benchmark.flags, store, financials.nace_code)
    projections = compute_projections(actions, financials)
    proj_summary = format_projections_summary(projections)

    # Briefing
    try:
        narrative, grounding_passed = await generate_briefing(analysis, benchmark)
    except Exception as e:
        log.warning("Job %s: narrative failed for %s: %s", job_id, financials.company_name, e)
        narrative = f"[Narrative generation failed: {e}]"

    # Deep recommendations (detailed Doktorarbeit sections)
    try:
        deep_recs = await generate_deep_recommendations(analysis, benchmark, projections)
    except Exception as e:
        log.warning("Job %s: deep recommendations failed: %s", job_id, e)
        deep_recs = ""

    return CompanyReport(
        company_name=financials.company_name,
        nace_code=financials.nace_code,
        ratios=[r.__dict__ if hasattr(r, '__dict__') else dict(r) for r in analysis.ratios if not r.not_derivable],
        flags=[f.__dict__ if hasattr(f, '__dict__') else {} for f in benchmark.flags],
        projections=[{
            "metric": p.metric,
            "current_value": p.current_value,
            "unit": p.action.unit,
            "description": p.action.description,
            "disclaimer": p.disclaimer,
            "scenarios": [s.__dict__ for s in p.scenarios],
        } for p in projections],
        narrative=narrative,
        recommendations_detail=deep_recs,
    )


async def run_background_job(job_id: str, filename: str, content: bytes) -> None:
    """Main background job entry point. Called from FastAPI background tasks."""
    t_start = time.monotonic()
    update_job(job_id, status="running", current_stage="starting")
    _evt(job_id, "job_started", filename=filename)
    log.info("Job %s started: %s (%d bytes)", job_id, filename, len(content))

    try:
        # Extract batches
        update_job(job_id, current_stage="extracting_zip")
        if filename.lower().endswith(".zip"):
            _evt(job_id, "stage_started", stage="zip_extraction")
            batches = extract_zip(content)
            _evt(job_id, "stage_done", stage="zip_extraction",
                 company_count=len(batches))
        else:
            # Single file — wrap in a batch
            batches = [CompanyBatch(company_hint="", files=[(filename, content)])]

        update_job(job_id, company_count=len(batches))
        _evt(job_id, "companies_discovered", count=len(batches),
             names=[b.company_hint for b in batches])

        store = BenchmarkStore(data_dir=BENCHMARK_DIR)
        company_reports = []

        for i, batch in enumerate(batches):
            update_job(job_id, companies_done=i,
                       current_stage=f"analysing_{batch.company_hint}")
            _evt(job_id, "company_started", index=i, total=len(batches),
                 company=batch.company_hint)

            report = await _process_company_batch(batch, store, job_id)
            if report:
                company_reports.append(report)
                _evt(job_id, "company_complete", company=report.company_name,
                     flags=len(report.flags), projections=len(report.projections))

            update_job(job_id, companies_done=i + 1)

        if not company_reports:
            raise ValueError("No companies could be successfully analysed")

        # Portfolio summary (if multiple companies)
        portfolio_summary = ""
        if len(company_reports) > 1:
            update_job(job_id, current_stage="portfolio_summary")
            _evt(job_id, "stage_started", stage="portfolio_summary")
            try:
                from backend.llm import router as llm_router
                names = ", ".join(c.company_name for c in company_reports)
                flag_counts = sum(len(c.flags) for c in company_reports)
                portfolio_summary = await llm_router.narrate(
                    f"Write a 200-word portfolio executive summary for these {len(company_reports)} companies: {names}. "
                    f"Total flags raised: {flag_counts}. Be concise and focus on cross-company patterns."
                )
            except Exception as e:
                log.warning("Portfolio summary failed: %s", e)

        # Generate PDF
        update_job(job_id, current_stage="generating_pdf")
        _evt(job_id, "stage_started", stage="pdf_generation")

        from datetime import datetime
        report_obj = AnalysisReport(
            title=f"Financial Analysis Report -- {', '.join(c.company_name for c in company_reports[:3])}"
                  + (f" +{len(company_reports)-3} more" if len(company_reports) > 3 else ""),
            generated_at=datetime.now().strftime("%d %B %Y, %H:%M UTC"),
            source_file=filename,
            companies=company_reports,
            portfolio_summary=portfolio_summary,
        )

        pdf_path = generate_pdf(report_obj, job_id)
        duration = int((time.monotonic() - t_start) / 60)

        update_job(job_id, status="complete", current_stage="done",
                   result_path=str(pdf_path), companies_done=len(batches))
        _evt(job_id, "job_complete",
             company_count=len(company_reports),
             pdf_path=str(pdf_path),
             duration_minutes=duration)
        log.info("Job %s complete in %d min: %s", job_id, duration, pdf_path)

    except Exception as e:
        log.error("Job %s failed: %s", job_id, e, exc_info=True)
        update_job(job_id, status="error", error=str(e), current_stage="failed")
        _evt(job_id, "job_error", error=str(e))
