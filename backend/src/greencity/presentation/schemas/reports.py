"""Pydantic schemas for explainable analysis reports."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DriverExplanationSchema(BaseModel):
    """One indicator explained as a GDS driver."""

    key: str
    label: str
    raw_value: float
    weighted_points: float
    direction: str
    explanation: str


class AnalysisReportResponse(BaseModel):
    """Public explainable report representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_job_id: UUID
    aoi_id: UUID
    scoring_profile_id: UUID
    headline: str
    executive_summary: str
    priority_band: str
    score: float
    drivers: list[dict[str, Any]]
    recommendations: list[str]
    methodology_notes: str
    source: str
    created_at: datetime
    updated_at: datetime


class GenerateReportRequest(BaseModel):
    """Body for ``POST /reports`` (generate from an analysis job)."""

    analysis_job_id: UUID
    vegetation_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    green_area_m2: float | None = Field(default=None, ge=0.0)
    park_walk_distance_m: float = Field(default=300.0, gt=0.0)
    aoi_name: str | None = Field(default=None, max_length=200)
