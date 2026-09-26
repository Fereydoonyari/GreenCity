"""Pydantic schemas for Green Deficiency Score / ranking endpoints."""

from uuid import UUID

from pydantic import BaseModel, Field

from greencity.presentation.schemas.indicators import IndicatorValuesSchema


class ScoreAoiRequest(BaseModel):
    """Body for scoring a single AOI."""

    scoring_profile_id: UUID
    vegetation_coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    green_area_m2: float | None = Field(default=None, ge=0.0)
    park_walk_distance_m: float = Field(default=300.0, gt=0.0)


class IndicatorContributionSchema(BaseModel):
    """One indicator's contribution to the GDS."""

    key: str
    raw_value: float
    normalised: float
    deficiency_component: float
    weight: float
    weighted_contribution: float
    direction: str


class GreenDeficiencyScoreSchema(BaseModel):
    """0–100 Green Deficiency Score with per-indicator breakdown."""

    score: float
    priority_band: str
    normalisation: str
    contributions: list[IndicatorContributionSchema]


class ScoreAoiResponse(BaseModel):
    """GDS result for one AOI."""

    aoi_id: UUID
    scoring_profile_id: UUID
    green_deficiency_score: GreenDeficiencyScoreSchema
    indicators: IndicatorValuesSchema
    vegetation_source: str
    green_area_source: str


class RankItemRequest(BaseModel):
    """One neighborhood candidate with precomputed indicators."""

    id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    indicators: IndicatorValuesSchema


class RankNeighborhoodsRequest(BaseModel):
    """Body for ranking multiple neighborhoods."""

    scoring_profile_id: UUID
    items: list[RankItemRequest] = Field(min_length=1)


class RankedNeighborhoodSchema(BaseModel):
    """One ranked neighborhood."""

    id: str
    label: str
    rank: int
    green_deficiency_score: GreenDeficiencyScoreSchema
    indicators: IndicatorValuesSchema


class RankNeighborhoodsResponse(BaseModel):
    """Ranked list of neighborhoods (rank 1 = highest priority)."""

    scoring_profile_id: UUID
    rankings: list[RankedNeighborhoodSchema]
