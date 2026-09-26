"""Pydantic schemas for Area of Interest HTTP resources."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from greencity.domain.entities.aoi import AoiKind


class AreaOfInterestCreateRequest(BaseModel):
    """Body for ``POST /areas-of-interest``."""

    project_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    geometry: dict[str, Any] = Field(
        description="GeoJSON Polygon, MultiPolygon, Feature, or single-Feature FeatureCollection."
    )
    kind: AoiKind = AoiKind.NEIGHBORHOOD
    parent_aoi_id: UUID | None = None


class AreaOfInterestUpdateRequest(BaseModel):
    """Body for ``PATCH /areas-of-interest/{id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    geometry: dict[str, Any] | None = None


class AreaOfInterestResponse(BaseModel):
    """Public AOI representation including GeoJSON geometry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: str
    kind: AoiKind
    parent_aoi_id: UUID | None
    geometry: dict[str, Any]
    created_at: datetime
    updated_at: datetime
