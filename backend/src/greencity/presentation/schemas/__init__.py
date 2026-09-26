"""Pydantic response/request schemas for the HTTP API."""

from greencity.presentation.schemas.analysis_jobs import (
    AnalysisJobCreateRequest,
    AnalysisJobFailRequest,
    AnalysisJobProgressRequest,
    AnalysisJobResponse,
)
from greencity.presentation.schemas.aois import (
    AreaOfInterestCreateRequest,
    AreaOfInterestResponse,
    AreaOfInterestUpdateRequest,
)
from greencity.presentation.schemas.health import HealthResponse
from greencity.presentation.schemas.projects import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from greencity.presentation.schemas.scoring_profiles import (
    IndicatorWeightsSchema,
    ScoringProfileCreateRequest,
    ScoringProfileResponse,
    ScoringProfileUpdateRequest,
)
from greencity.presentation.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest

__all__ = [
    "AnalysisJobCreateRequest",
    "AnalysisJobFailRequest",
    "AnalysisJobProgressRequest",
    "AnalysisJobResponse",
    "AreaOfInterestCreateRequest",
    "AreaOfInterestResponse",
    "AreaOfInterestUpdateRequest",
    "HealthResponse",
    "IndicatorWeightsSchema",
    "ProjectCreateRequest",
    "ProjectResponse",
    "ProjectUpdateRequest",
    "ScoringProfileCreateRequest",
    "ScoringProfileResponse",
    "ScoringProfileUpdateRequest",
    "UserCreateRequest",
    "UserResponse",
    "UserUpdateRequest",
]
