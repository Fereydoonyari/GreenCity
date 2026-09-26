"""Pydantic schemas for Analysis Job HTTP resources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from greencity.domain.entities.analysis_job import AnalysisJobStatus


class AnalysisJobCreateRequest(BaseModel):
    """Body for ``POST /analysis-jobs``."""

    project_id: UUID
    aoi_id: UUID
    scoring_profile_id: UUID


class AnalysisJobProgressRequest(BaseModel):
    """Body for ``PATCH /analysis-jobs/{id}/progress``."""

    current_step: str = Field(min_length=1, max_length=100)
    progress_pct: int = Field(ge=0, le=100)


class AnalysisJobFailRequest(BaseModel):
    """Body for ``POST /analysis-jobs/{id}/fail``."""

    message: str = Field(min_length=1, max_length=2000)


class AnalysisJobResponse(BaseModel):
    """Public analysis job representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    aoi_id: UUID
    scoring_profile_id: UUID
    status: AnalysisJobStatus
    current_step: str
    progress_pct: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
