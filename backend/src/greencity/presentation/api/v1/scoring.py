"""HTTP endpoints for Green Deficiency Score and neighborhood ranking."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from greencity.application.use_cases.scoring import (
    RankItemInput,
    RankNeighborhoodsCommand,
    RankNeighborhoodsUseCase,
    ScoreAoiCommand,
    ScoreAoiResult,
    ScoreAoiUseCase,
)
from greencity.domain.services.scoring import GreenDeficiencyScore, RankedNeighborhood
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.presentation.dependencies import (
    provide_rank_neighborhoods_use_case,
    provide_score_aoi_use_case,
)
from greencity.presentation.schemas.indicators import IndicatorValuesSchema
from greencity.presentation.schemas.scoring import (
    GreenDeficiencyScoreSchema,
    IndicatorContributionSchema,
    RankedNeighborhoodSchema,
    RankNeighborhoodsRequest,
    RankNeighborhoodsResponse,
    ScoreAoiRequest,
    ScoreAoiResponse,
)

router = APIRouter(prefix="/scoring", tags=["scoring"])


def _score_schema(gds: GreenDeficiencyScore) -> GreenDeficiencyScoreSchema:
    return GreenDeficiencyScoreSchema(
        score=gds.score,
        priority_band=gds.priority_band,
        normalisation=gds.normalisation,
        contributions=[
            IndicatorContributionSchema(
                key=c.key,
                raw_value=c.raw_value,
                normalised=c.normalised,
                deficiency_component=c.deficiency_component,
                weight=c.weight,
                weighted_contribution=c.weighted_contribution,
                direction=c.direction.value,
            )
            for c in gds.contributions
        ],
    )


def _indicators_schema(values: IndicatorValues) -> IndicatorValuesSchema:
    return IndicatorValuesSchema(**values.as_dict())


def _score_response(result: ScoreAoiResult) -> ScoreAoiResponse:
    return ScoreAoiResponse(
        aoi_id=result.aoi_id,
        scoring_profile_id=result.scoring_profile_id,
        green_deficiency_score=_score_schema(result.score),
        indicators=_indicators_schema(result.indicators),
        vegetation_source=result.vegetation_source,
        green_area_source=result.green_area_source,
    )


def _ranked_schema(item: RankedNeighborhood) -> RankedNeighborhoodSchema:
    return RankedNeighborhoodSchema(
        id=item.id,
        label=item.label,
        rank=item.rank,
        green_deficiency_score=_score_schema(item.score),
        indicators=_indicators_schema(item.indicators),
    )


@router.post(
    "/aois/{aoi_id}/score",
    response_model=ScoreAoiResponse,
    summary="Compute Green Deficiency Score for an AOI",
)
def score_aoi(
    aoi_id: UUID,
    body: ScoreAoiRequest,
    use_case: Annotated[ScoreAoiUseCase, Depends(provide_score_aoi_use_case)],
) -> ScoreAoiResponse:
    """Compute indicators for the AOI, then apply the scoring profile weights."""

    result = use_case.execute(
        ScoreAoiCommand(
            aoi_id=aoi_id,
            scoring_profile_id=body.scoring_profile_id,
            vegetation_coverage=body.vegetation_coverage,
            green_area_m2=body.green_area_m2,
            park_walk_distance_m=body.park_walk_distance_m,
        )
    )
    return _score_response(result)


@router.post(
    "/rank",
    response_model=RankNeighborhoodsResponse,
    summary="Rank neighborhoods by Green Deficiency Score",
)
def rank_neighborhoods_endpoint(
    body: RankNeighborhoodsRequest,
    use_case: Annotated[RankNeighborhoodsUseCase, Depends(provide_rank_neighborhoods_use_case)],
) -> RankNeighborhoodsResponse:
    """Rank candidates (highest GDS = rank 1). Uses cohort min–max when N ≥ 2."""

    items = tuple(
        RankItemInput(
            id=item.id,
            label=item.label,
            indicators=IndicatorValues(**item.indicators.model_dump()),
        )
        for item in body.items
    )
    rankings = use_case.execute(
        RankNeighborhoodsCommand(
            scoring_profile_id=body.scoring_profile_id,
            items=items,
        )
    )
    return RankNeighborhoodsResponse(
        scoring_profile_id=body.scoring_profile_id,
        rankings=[_ranked_schema(r) for r in rankings],
    )
