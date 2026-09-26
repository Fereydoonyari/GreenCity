"""Pydantic schemas for indicator computation endpoints."""

from uuid import UUID

from pydantic import BaseModel, Field


class ComputeIndicatorsRequest(BaseModel):
    """Optional vegetation overrides for indicator computation."""

    vegetation_coverage: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="NDVI vegetated fraction. Falls back to OSM park coverage when omitted.",
    )
    green_area_m2: float | None = Field(
        default=None,
        ge=0.0,
        description="Green area in m². Falls back to OSM park area when omitted.",
    )
    park_walk_distance_m: float = Field(
        default=300.0,
        gt=0.0,
        description="Walk distance (m) used for park accessibility buffers.",
    )


class IndicatorValuesSchema(BaseModel):
    """The four canonical scored indicator measurements."""

    vegetation_coverage: float
    green_area_per_m2: float
    road_density: float
    built_up_ratio: float


class IndicatorComputationResponse(BaseModel):
    """Full indicator computation result for an AOI."""

    aoi_id: UUID
    indicators: IndicatorValuesSchema
    vegetation_source: str
    green_area_source: str
    aoi_area_m2: float
    road_count: int
    park_count: int
    building_count: int
    vegetation_mask: dict | None = None
    vegetation_hotspot_mask: dict | None = None
    park_access_mask: dict | None = None
    heat_exposure_mask: dict | None = None
    mean_nearest_park_distance_m: float | None = None
    median_nearest_park_distance_m: float | None = None
    mean_nearest_park_walk_min: float | None = None
    median_nearest_park_walk_min: float | None = None
    mean_lst_c: float | None = None
    heat_source: str = ""
