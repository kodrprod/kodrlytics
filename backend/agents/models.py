"""Data models for the multi-agent room pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    search_queries: list[str] = field(default_factory=list)
    assigned_worker: str = ""
    status: str = "pending"  # pending|done|failed
    result: str = ""


@dataclass
class PipelineContext:
    filename: str
    content: bytes
    document_text: str = ""
    company_hint: str = ""
    # Structured financial data
    financials: Optional[Any] = None        # CompanyFinancials
    reconciliation: Optional[Any] = None    # ReconciliationResult
    analysis: Optional[Any] = None          # AnalysisResult
    benchmark: Optional[Any] = None         # BenchmarkResult
    actions: list = field(default_factory=list)
    projections: list = field(default_factory=list)
    proj_summary: str = ""
    # Multi-document dataset (ZIP ingestion)
    dataset: Optional[Any] = None           # DatasetContext from zip_ingester
    # CEO plan and room briefs
    ceo_plan: str = ""
    room_briefs: dict[str, str] = field(default_factory=dict)
    # Accumulated room reports
    room_reports: dict[str, str] = field(default_factory=dict)
