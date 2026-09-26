"""Pydantic schemas for Scoring Profile HTTP resources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IndicatorWeightsSchema(BaseModel):
    """HTTP representation of indicator weights (must sum to 1.0)."""

    vegetation_coverage: float = Field(ge=0)
    green_area_per_m2: float = Field(ge=0)
    road_density: float = Field(ge=0)
    built_up_ratio: float = Field(ge=0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> IndicatorWeightsSchema:
        """Validate that weights approximately sum to 1.0 at the API boundary."""

        total = (
            self.vegetation_coverage
            + self.green_area_per_m2
            + self.road_density
            + self.built_up_ratio
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Indicator weights must sum to 1.0 (received {total:.6f}).")
        return self


class ScoringProfileCreateRequest(BaseModel):
    """Body for ``POST /scoring-profiles`` (owner is the authenticated user)."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    weights: IndicatorWeightsSchema | None = None
    is_default: bool = False
    use_balanced_defaults: bool = False

    @model_validator(mode="after")
    def require_weights_or_defaults(self) -> ScoringProfileCreateRequest:
        """Require either explicit weights or the balanced-defaults flag."""

        if self.use_balanced_defaults and self.weights is not None:
            raise ValueError("Provide either weights or use_balanced_defaults, not both.")
        if not self.use_balanced_defaults and self.weights is None:
            raise ValueError("weights is required unless use_balanced_defaults is true.")
        return self


class ScoringProfileUpdateRequest(BaseModel):
    """Body for ``PATCH /scoring-profiles/{id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    weights: IndicatorWeightsSchema | None = None
    is_default: bool | None = None


class ScoringProfileResponse(BaseModel):
    """Public scoring profile representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    description: str
    weights: IndicatorWeightsSchema
    is_default: bool
    created_at: datetime
    updated_at: datetime
