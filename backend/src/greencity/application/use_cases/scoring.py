"""Use cases for Green Deficiency Score and neighborhood ranking."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.application.use_cases.indicators import (
    ComputeIndicatorsCommand,
    ComputeIndicatorsUseCase,
    IndicatorComputationResult,
)
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.services.scoring import (
    GreenDeficiencyScore,
    RankedNeighborhood,
    compute_green_deficiency_score,
    rank_neighborhoods,
)
from greencity.domain.value_objects.indicator_weights import IndicatorWeights
from greencity.domain.value_objects.indicators import IndicatorValues


@dataclass(frozen=True)
class ScoreAoiCommand:
    """Score a single AOI with a scoring profile."""

    aoi_id: UUID
    scoring_profile_id: UUID
    vegetation_coverage: float | None = None
    green_area_m2: float | None = None
    park_walk_distance_m: float = 300.0


@dataclass(frozen=True)
class ScoreAoiResult:
    """GDS for one AOI plus the indicator computation context."""

    aoi_id: UUID
    scoring_profile_id: UUID
    score: GreenDeficiencyScore
    indicators: IndicatorValues
    vegetation_source: str
    green_area_source: str


@dataclass(frozen=True)
class RankItemInput:
    """One candidate neighborhood for ranking."""

    id: str
    label: str
    indicators: IndicatorValues


@dataclass(frozen=True)
class RankNeighborhoodsCommand:
    """Rank multiple neighborhoods using a scoring profile."""

    scoring_profile_id: UUID
    items: tuple[RankItemInput, ...]


class ScoreAoiUseCase:
    """Compute indicators for an AOI, then apply the Green Deficiency Score."""

    def __init__(
        self,
        uow: UnitOfWork,
        compute_indicators: ComputeIndicatorsUseCase,
    ) -> None:
        self._uow = uow
        self._compute_indicators = compute_indicators

    def execute(self, command: ScoreAoiCommand) -> ScoreAoiResult:
        """Return the GDS for ``command.aoi_id`` using the given profile."""

        profile = self._uow.scoring_profiles.get_by_id(command.scoring_profile_id)
        if profile is None:
            raise NotFoundError(
                f"Scoring profile '{command.scoring_profile_id}' was not found."
            )

        computation: IndicatorComputationResult = self._compute_indicators.execute(
            ComputeIndicatorsCommand(
                aoi_id=command.aoi_id,
                vegetation_coverage=command.vegetation_coverage,
                green_area_m2=command.green_area_m2,
                park_walk_distance_m=command.park_walk_distance_m,
            )
        )
        gds = compute_green_deficiency_score(computation.indicators, profile.weights)
        return ScoreAoiResult(
            aoi_id=command.aoi_id,
            scoring_profile_id=command.scoring_profile_id,
            score=gds,
            indicators=computation.indicators,
            vegetation_source=computation.vegetation_source,
            green_area_source=computation.green_area_source,
        )


class RankNeighborhoodsUseCase:
    """Rank precomputed neighborhood indicators by Green Deficiency Score."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, command: RankNeighborhoodsCommand) -> list[RankedNeighborhood]:
        """Return neighborhoods ranked 1..N (1 = highest deficiency)."""

        if not command.items:
            raise ValidationError("At least one neighborhood item is required.")

        profile = self._uow.scoring_profiles.get_by_id(command.scoring_profile_id)
        if profile is None:
            raise NotFoundError(
                f"Scoring profile '{command.scoring_profile_id}' was not found."
            )

        ids = [item.id for item in command.items]
        if len(ids) != len(set(ids)):
            raise ValidationError("Neighborhood item ids must be unique.")

        payload = [(item.id, item.label, item.indicators) for item in command.items]
        return rank_neighborhoods(payload, profile.weights)


def score_indicators(
    indicators: IndicatorValues,
    weights: IndicatorWeights,
) -> GreenDeficiencyScore:
    """Convenience wrapper for callers that already have indicators + weights."""

    return compute_green_deficiency_score(indicators, weights)
