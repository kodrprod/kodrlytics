"""FastAPI application — pipeline API + WebSocket event stream + long-running job API."""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.pipeline.orchestrator import run_pipeline
from backend.pipeline.events import RunErrorEvent
from backend.pipeline.job_store import create_job, get_job, update_job
from backend.pipeline.background_runner import run_background_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kodrlytics Financial Analysis API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://85.215.162.173", "http://85.215.162.173:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for quick WebSocket runs (single-file, not ZIP)
_pending_runs: dict[str, tuple[str, bytes]] = {}

SAMPLE_PATH = Path(__file__).parent.parent.parent / "data" / "samples" / "mustermann_gmbh.json"


class RunCreated(BaseModel):
    run_id: str


class JobCreated(BaseModel):
    job_id: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    filename: str
    company_count: int
    companies_done: int
    current_stage: str
    error: str
    result_ready: bool
    recent_events: list[dict]


# ── Quick WebSocket runs (existing behaviour, single file) ─────────────────────

@app.post("/runs", response_model=RunCreated)
async def create_run(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large for quick run (max 20 MB). Use /jobs for large files.")
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = (file.filename or "upload", content)
    return RunCreated(run_id=run_id)


@app.post("/runs/sample", response_model=RunCreated)
async def create_sample_run():
    content = SAMPLE_PATH.read_bytes()
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = ("mustermann_gmbh.json", content)
    return RunCreated(run_id=run_id)


@app.websocket("/ws/{run_id}")
async def pipeline_ws(websocket: WebSocket, run_id: str):
    await websocket.accept()
    if run_id not in _pending_runs:
        await websocket.send_json(RunErrorEvent(
            run_id=run_id, stage="api", error=f"Unknown run_id: {run_id}"
        ).model_dump())
        await websocket.close()
        return

    filename, content = _pending_runs.pop(run_id)
    try:
        async for event in run_pipeline(filename, content, run_id=run_id):
            try:
                await websocket.send_json(event.model_dump())
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json(RunErrorEvent(
                run_id=run_id, stage="unknown", error=str(e)
            ).model_dump())
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ── Long-running jobs (ZIP + large files) ─────────────────────────────────────

@app.post("/jobs", response_model=JobCreated)
async def create_job_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Submit a file (ZIP, CSV, Excel, PDF) for deep background analysis.
    Returns a job_id immediately. Poll /jobs/{job_id} for status.
    Large ZIPs with multiple companies may take minutes to hours.
    """
    content = await file.read()
    filename = file.filename or "upload"

    # Size limits: 2 GB
    if len(content) > 2 * 1024 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 2 GB)")

    job_id = str(uuid.uuid4())
    create_job(job_id, filename)

    background_tasks.add_task(run_background_job, job_id, filename, content)

    return JobCreated(
        job_id=job_id,
        message=f"Job queued. Poll GET /jobs/{job_id} for progress. PDF will be available at GET /jobs/{job_id}/report when complete."
    )


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Poll job status and recent events."""
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Job not found")
    recent_events = json.loads(rec.events_json)[-20:]
    return JobStatus(
        job_id=rec.job_id,
        status=rec.status,
        filename=rec.filename,
        company_count=rec.company_count,
        companies_done=rec.companies_done,
        current_stage=rec.current_stage,
        error=rec.error,
        result_ready=rec.status == "complete" and bool(rec.result_path),
        recent_events=recent_events,
    )


@app.get("/jobs/{job_id}/report")
async def download_report(job_id: str):
    """Download the generated PDF report."""
    rec = get_job(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Job not found")
    if rec.status != "complete":
        raise HTTPException(status_code=202, detail=f"Job not complete yet (status: {rec.status})")
    pdf_path = Path(rec.result_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"kodrlytics_report_{job_id[:8]}.pdf",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}


# ── Room-based multi-agent pipeline ───────────────────────────────────────────

@app.post("/runs-rooms", response_model=RunCreated)
async def create_rooms_run(file: UploadFile = File(None)):
    """Submit a file for the room-based agent pipeline. Returns run_id for /ws-rooms/{run_id}.
    If no file is uploaded, the built-in Mustermann GmbH sample is used."""
    if file and file.filename:
        content = await file.read()
        filename = file.filename
    else:
        content = SAMPLE_PATH.read_bytes()
        filename = "mustermann_gmbh.json"
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = (filename, content)
    return RunCreated(run_id=run_id)


@app.websocket("/ws-rooms/{run_id}")
async def rooms_pipeline_ws(websocket: WebSocket, run_id: str):
    """Room-based multi-agent pipeline — 6 rooms, manager + workers, web search."""
    from datetime import datetime, timezone
    await websocket.accept()

    if run_id not in _pending_runs:
        await websocket.send_json({
            "event_type": "run_error", "run_id": run_id, "stage": "api",
            "error": f"Unknown run_id: {run_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await websocket.close()
        return

    filename, content = _pending_runs.pop(run_id)

    async def emit(event_dict: dict) -> None:
        event_dict.setdefault("run_id", run_id)
        event_dict.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        try:
            await websocket.send_json(event_dict)
        except Exception:
            pass

    try:
        from backend.agents.pipeline import run_room_pipeline
        await run_room_pipeline(filename, content, run_id, emit)
    except WebSocketDisconnect:
        logger.info("Client disconnected from rooms run %s", run_id)
    except Exception as e:
        logger.error("Rooms pipeline error for %s: %s", run_id, e)
        await emit({"event_type": "run_error", "stage": "pipeline", "error": str(e)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
