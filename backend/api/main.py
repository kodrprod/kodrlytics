"""FastAPI application — pipeline API + WebSocket event stream."""
from __future__ import annotations
import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.pipeline.orchestrator import run_pipeline
from backend.pipeline.events import RunErrorEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kodrlytics Financial Analysis API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store: run_id → (filename, content). In production this would be Redis/S3.
_pending_runs: dict[str, tuple[str, bytes]] = {}

SAMPLE_PATH = Path(__file__).parent.parent.parent / "data" / "samples" / "mustermann_gmbh.json"


class RunCreated(BaseModel):
    run_id: str


@app.post("/runs", response_model=RunCreated)
async def create_run(file: UploadFile = File(...)):
    """Accept a financial statement file, store it, return a run_id."""
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = (file.filename or "upload.csv", content)
    return RunCreated(run_id=run_id)


@app.post("/runs/sample", response_model=RunCreated)
async def create_sample_run():
    """Start a run on the built-in Mustermann GmbH sample (no upload needed)."""
    content = SAMPLE_PATH.read_bytes()
    run_id = str(uuid.uuid4())
    _pending_runs[run_id] = ("mustermann_gmbh.json", content)
    return RunCreated(run_id=run_id)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/{run_id}")
async def pipeline_ws(websocket: WebSocket, run_id: str):
    """Stream pipeline events for a given run_id over WebSocket."""
    await websocket.accept()

    if run_id not in _pending_runs:
        await websocket.send_json(RunErrorEvent(
            run_id=run_id, stage="api",
            error=f"Unknown run_id: {run_id}"
        ).model_dump())
        await websocket.close()
        return

    filename, content = _pending_runs.pop(run_id)

    try:
        async for event in run_pipeline(filename, content, run_id=run_id):
            try:
                await websocket.send_json(event.model_dump())
            except Exception:
                break  # client disconnected
    except WebSocketDisconnect:
        logger.info("Client disconnected for run %s", run_id)
    except Exception as e:
        logger.error("Pipeline error for run %s: %s", run_id, e)
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
