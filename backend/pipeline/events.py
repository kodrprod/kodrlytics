"""WebSocket event models emitted by the pipeline orchestrator."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseEvent(BaseModel):
    run_id: str
    timestamp: str = Field(default_factory=_now)


class StageStartedEvent(BaseEvent):
    event_type: Literal["stage_started"] = "stage_started"
    stage: str          # "intake" | "analysis" | "benchmark" | "strategy" | "briefing"
    stage_index: int    # 0-4


class DataPassedEvent(BaseEvent):
    event_type: Literal["data_passed"] = "data_passed"
    from_stage: str
    to_stage: str
    summary: str        # human-readable e.g. "3 years of financials extracted"


class FindingCreatedEvent(BaseEvent):
    event_type: Literal["finding_created"] = "finding_created"
    stage: str
    finding_id: str
    name: str
    value: Optional[float]
    unit: str
    period: str


class FlagRaisedEvent(BaseEvent):
    event_type: Literal["flag_raised"] = "flag_raised"
    stage: str
    flag_type: str
    severity: str       # "warning" | "critical"
    message: str
    metric: str


class StageDoneEvent(BaseEvent):
    event_type: Literal["stage_done"] = "stage_done"
    stage: str
    stage_index: int
    duration_ms: int


class RunErrorEvent(BaseEvent):
    event_type: Literal["run_error"] = "run_error"
    stage: str
    error: str


class RunCompleteEvent(BaseEvent):
    event_type: Literal["run_complete"] = "run_complete"
    company_name: str
    total_duration_ms: int
    finding_count: int
    flag_count: int
    # Full results payload (serialized)
    ratios: list[dict]
    flags: list[dict]
    projections: list[dict]
    narrative: str


class RoomOpenedEvent(BaseEvent):
    event_type: Literal["room_opened"] = "room_opened"
    room_name: str
    stage: int
    worker_count: int
    task_count: int


class WorkerSpawnedEvent(BaseEvent):
    event_type: Literal["worker_spawned"] = "worker_spawned"
    room_name: str
    stage: int
    worker_id: str
    task_title: str


class WorkerLearningEvent(BaseEvent):
    event_type: Literal["worker_learning"] = "worker_learning"
    room_name: str
    stage: int
    worker_id: str
    queries: list[str]


class WorkerWorkingEvent(BaseEvent):
    event_type: Literal["worker_working"] = "worker_working"
    room_name: str
    stage: int
    worker_id: str
    task_title: str


class WorkerDoneEvent(BaseEvent):
    event_type: Literal["worker_done"] = "worker_done"
    room_name: str
    stage: int
    worker_id: str
    task_title: str


class ManagerWritingEvent(BaseEvent):
    event_type: Literal["manager_writing"] = "manager_writing"
    room_name: str
    stage: int


class RoomClosedEvent(BaseEvent):
    event_type: Literal["room_closed"] = "room_closed"
    room_name: str
    stage: int
    worker_count: int


PipelineEvent = Union[
    StageStartedEvent, DataPassedEvent, FindingCreatedEvent,
    FlagRaisedEvent, StageDoneEvent, RunErrorEvent, RunCompleteEvent,
    RoomOpenedEvent, WorkerSpawnedEvent, WorkerLearningEvent,
    WorkerWorkingEvent, WorkerDoneEvent, ManagerWritingEvent, RoomClosedEvent,
]
