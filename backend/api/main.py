"""FastAPI — single unified analysis pipeline with WebSocket event streaming."""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kodrlytics Financial Analysis API", version="0.5.0")

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_pending_runs: dict[str, tuple[str, bytes]] = {}

SAMPLE_PATH = Path(__file__).parent.parent.parent / "data" / "samples" / "mustermann_gmbh.json"


class RunCreated(BaseModel):
    run_id: str


# ── Submit a run (file or sample) ─────────────────────────────────────────────

@app.post("/runs-rooms", response_model=RunCreated)
async def create_rooms_run(file: UploadFile = File(None)):
    """Submit any file (single, ZIP, PDF, Excel, JSON) for analysis.
    Returns run_id for /ws-rooms/{run_id}."""
    if file and file.filename:
        content = await file.read()
        filename = file.filename
    else:
        content = SAMPLE_PATH.read_bytes()
        filename = "mustermann_gmbh.json"
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = (filename, content)
    return RunCreated(run_id=run_id)


@app.post("/runs/sample", response_model=RunCreated)
async def create_sample_run():
    content = SAMPLE_PATH.read_bytes()
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = ("mustermann_gmbh.json", content)
    return RunCreated(run_id=run_id)


# Keep legacy /runs endpoint for compatibility
@app.post("/runs", response_model=RunCreated)
async def create_run(file: UploadFile = File(...)):
    content = await file.read()
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = (file.filename or "upload", content)
    return RunCreated(run_id=run_id)


# ── WebSocket pipeline ────────────────────────────────────────────────────────

@app.websocket("/ws-rooms/{run_id}")
async def rooms_pipeline_ws(websocket: WebSocket, run_id: str):
    """Multi-agent room pipeline: CEO + 6 rooms + 20 workers each."""
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
        logger.info("Client disconnected from run %s", run_id)
    except Exception as e:
        logger.error("Pipeline error for %s: %s", run_id, e)
        await emit({"event_type": "run_error", "stage": "pipeline", "error": str(e)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Keep legacy WebSocket for compatibility
@app.websocket("/ws/{run_id}")
async def legacy_pipeline_ws(websocket: WebSocket, run_id: str):
    await rooms_pipeline_ws(websocket, run_id)


# ── Report downloads ──────────────────────────────────────────────────────────

@app.get("/reports/{run_id}.pdf")
async def download_pdf(run_id: str):
    path = REPORTS_DIR / f"{run_id}.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF report not found — run may still be in progress")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"kodrlytics_{run_id[:8]}.pdf",
    )


@app.get("/reports/{run_id}.docx")
async def download_docx(run_id: str):
    path = REPORTS_DIR / f"{run_id}.docx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="DOCX report not found — run may still be in progress")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"kodrlytics_{run_id[:8]}.docx",
    )


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.5.0"}
