"""SQLite-backed job store for long-running analysis jobs."""
from __future__ import annotations
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "jobs.db"


@dataclass
class JobRecord:
    job_id: str
    status: str          # queued | running | complete | error
    created_at: float
    updated_at: float
    filename: str
    company_count: int = 0
    companies_done: int = 0
    current_stage: str = ""
    error: str = ""
    result_path: str = ""   # path to generated PDF
    events_json: str = "[]" # serialized list of recent events for polling


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        status TEXT,
        created_at REAL,
        updated_at REAL,
        filename TEXT,
        company_count INTEGER DEFAULT 0,
        companies_done INTEGER DEFAULT 0,
        current_stage TEXT DEFAULT '',
        error TEXT DEFAULT '',
        result_path TEXT DEFAULT '',
        events_json TEXT DEFAULT '[]'
    )""")
    conn.commit()
    return conn


def create_job(job_id: str, filename: str) -> JobRecord:
    now = time.time()
    rec = JobRecord(job_id=job_id, status="queued",
                    created_at=now, updated_at=now, filename=filename)
    conn = _connect()
    conn.execute("""INSERT INTO jobs
        (job_id, status, created_at, updated_at, filename)
        VALUES (?,?,?,?,?)""",
        (rec.job_id, rec.status, rec.created_at, rec.updated_at, rec.filename))
    conn.commit()
    conn.close()
    return rec


def update_job(job_id: str, **kwargs) -> None:
    kwargs["updated_at"] = time.time()
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [job_id]
    conn = _connect()
    conn.execute(f"UPDATE jobs SET {sets} WHERE job_id=?", vals)
    conn.commit()
    conn.close()


def get_job(job_id: str) -> Optional[JobRecord]:
    conn = _connect()
    row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    conn.close()
    if not row:
        return None
    cols = ["job_id","status","created_at","updated_at","filename",
            "company_count","companies_done","current_stage","error","result_path","events_json"]
    return JobRecord(**dict(zip(cols, row)))


def append_event(job_id: str, event: dict) -> None:
    """Append an event to the job's event log (keep last 500)."""
    conn = _connect()
    row = conn.execute("SELECT events_json FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if not row:
        conn.close()
        return
    events = json.loads(row[0])
    events.append(event)
    events = events[-500:]
    conn.execute("UPDATE jobs SET events_json=?, updated_at=? WHERE job_id=?",
                 (json.dumps(events), time.time(), job_id))
    conn.commit()
    conn.close()
