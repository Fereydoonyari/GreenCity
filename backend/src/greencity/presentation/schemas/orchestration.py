"""Pydantic schemas for analysis orchestration run responses."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from greencity.presentation.schemas.analysis_jobs import AnalysisJobResponse
from greencity.presentation.schemas.indicators import IndicatorValuesSchema
from greencity.presentation.schemas.reports import AnalysisReportResponse
from greencity.presentation.schemas.scoring import GreenDeficiencyScoreSchema


class RunAnalysisRequest(BaseModel):
    """Optional vegetation overrides for an orchestration run."""

    vegetation_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    green_area_m2: float | None = Field(default=None, ge=0.0)
    park_walk_distance_m: float = Field(default=300.0, gt=0.0)
    auto_start: bool = Field(
        default=True,
        description="If true, start a queued job before orchestrating.",
    )


class AnalysisOrchestrationSchema(BaseModel):
    """Structured output from the LangGraph analysis agent."""

    aoi_id: UUID
    scoring_profile_id: UUID
    indicators: IndicatorValuesSchema
    green_deficiency_score: GreenDeficiencyScoreSchema
    steps_completed: list[str]
    summary: str
    vegetation_source: str
    green_area_source: str
    report: AnalysisReportResponse | None = None
    vegetation_mask: dict | None = Field(
        default=None,
        description="GeoJSON FeatureCollection of vegetated density patches (sparse/moderate/dense).",
    )
    vegetation_hotspot_mask: dict | None = Field(
        default=None,
        description="GeoJSON FeatureCollection of lowest-vegetation hotspot tiles.",
    )
    park_access_mask: dict | None = Field(
        default=None,
        description="GeoJSON tiles by distance to nearest OSM park (well_served/moderate/underserved).",
    )
    heat_exposure_mask: dict | None = Field(
        default=None,
        description="GeoJSON tiles of warmest Landsat LST areas within the AOI.",
    )
    mean_nearest_park_distance_m: float | None = Field(
        default=None,
        description="Mean Euclidean distance (m) from AOI sample points to nearest park.",
    )
    median_nearest_park_distance_m: float | None = None
    mean_nearest_park_walk_min: float | None = Field(
        default=None,
        description="Mean walking time (min) to nearest park at ~5 km/h.",
    )
    median_nearest_park_walk_min: float | None = None
    mean_lst_c: float | None = Field(
        default=None,
        description="Mean land-surface temperature (°C) from Landsat ST when available.",
    )
    heat_source: str = ""


class RunAnalysisResponse(BaseModel):
    """Job state after orchestration plus analysis results."""

    job: AnalysisJobResponse
    analysis: AnalysisOrchestrationSchema
