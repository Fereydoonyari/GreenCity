"""Agent narrative HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from greencity.application.use_cases.agent_narratives import (
    GenerateNeighborhoodBriefUseCase,
    GenerateNeighborhoodComparisonUseCase,
    GenerateVegetationPlanUseCase,
    NeighborhoodBriefCommand,
    NeighborhoodComparisonCommand,
    VegetationPlanCommand,
)
from greencity.domain.value_objects.agent_narrative import (
    AgentNarrative,
    CityLocation,
    NeighborhoodSnapshot,
)
from greencity.presentation.dependencies import (
    CurrentUser,
    provide_generate_neighborhood_brief_use_case,
    provide_generate_neighborhood_comparison_use_case,
    provide_generate_vegetation_plan_use_case,
)
from greencity.presentation.schemas.indicators import IndicatorValuesSchema

router = APIRouter(prefix="/agent", tags=["agent"])


class NeighborhoodSnapshotSchema(BaseModel):
    """Scored neighborhood facts for agent grounding."""

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    score: float = Field(ge=0, le=100)
    priority_band: str = Field(min_length=1, max_length=32)
    rank: int | None = Field(default=None, ge=1)
    indicators: IndicatorValuesSchema


class CityLocationSchema(BaseModel):
    """City centroid used for climate-aware planting plans."""

    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class NarrativeSectionSchema(BaseModel):
    """One titled section in an agent write-up."""

    title: str
    body: str


class AgentNarrativeSchema(BaseModel):
    """Structured agent response for the UI."""

    title: str
    kind: str
    focus_name: str | None = None
    sections: list[NarrativeSectionSchema]
    source: str


class NeighborhoodBriefRequest(BaseModel):
    """Body for ``POST /agent/neighborhood-brief``."""

    project_id: UUID
    focus: NeighborhoodSnapshotSchema
    peers: list[NeighborhoodSnapshotSchema] = Field(default_factory=list)


class NeighborhoodComparisonRequest(BaseModel):
    """Body for ``POST /agent/neighborhood-comparison``."""

    project_id: UUID
    neighborhoods: list[NeighborhoodSnapshotSchema] = Field(min_length=1)


class VegetationPlanRequest(BaseModel):
    """Body for ``POST /agent/vegetation-plan``."""

    project_id: UUID
    city: CityLocationSchema
    focus: NeighborhoodSnapshotSchema


def _to_snapshot(row: NeighborhoodSnapshotSchema) -> NeighborhoodSnapshot:
    return NeighborhoodSnapshot(
        id=row.id,
        name=row.name,
        score=row.score,
        priority_band=row.priority_band,
        rank=row.rank,
        vegetation_coverage=row.indicators.vegetation_coverage,
        green_area_per_m2=row.indicators.green_area_per_m2,
        road_density=row.indicators.road_density,
        built_up_ratio=row.indicators.built_up_ratio,
    )


def _to_schema(narrative: AgentNarrative) -> AgentNarrativeSchema:
    return AgentNarrativeSchema(
        title=narrative.title,
        kind=narrative.kind,
        focus_name=narrative.focus_name,
        sections=[
            NarrativeSectionSchema(title=section.title, body=section.body)
            for section in narrative.sections
        ],
        source=narrative.source,
    )


@router.post(
    "/neighborhood-brief",
    response_model=AgentNarrativeSchema,
    summary="Comprehensive agent analysis for one neighborhood vs peers",
)
def generate_neighborhood_brief(
    body: NeighborhoodBriefRequest,
    current_user: CurrentUser,
    use_case: Annotated[
        GenerateNeighborhoodBriefUseCase,
        Depends(provide_generate_neighborhood_brief_use_case),
    ],
) -> AgentNarrativeSchema:
    """Produce a full neighborhood character brief grounded in scored indicators."""

    narrative = use_case.execute(
        NeighborhoodBriefCommand(
            project_id=body.project_id,
            owner_id=current_user.id,
            focus=_to_snapshot(body.focus),
            peers=tuple(_to_snapshot(peer) for peer in body.peers),
        )
    )
    return _to_schema(narrative)


@router.post(
    "/neighborhood-comparison",
    response_model=AgentNarrativeSchema,
    summary="Agent comparison across all scored neighborhoods",
)
def generate_neighborhood_comparison(
    body: NeighborhoodComparisonRequest,
    current_user: CurrentUser,
    use_case: Annotated[
        GenerateNeighborhoodComparisonUseCase,
        Depends(provide_generate_neighborhood_comparison_use_case),
    ],
) -> AgentNarrativeSchema:
    """Produce a comprehensive comparison of the user's neighborhoods."""

    narrative = use_case.execute(
        NeighborhoodComparisonCommand(
            project_id=body.project_id,
            owner_id=current_user.id,
            neighborhoods=tuple(_to_snapshot(row) for row in body.neighborhoods),
        )
    )
    return _to_schema(narrative)


@router.post(
    "/vegetation-plan",
    response_model=AgentNarrativeSchema,
    summary="Geo-aware short/mid/long-term vegetation planting plan",
)
def generate_vegetation_plan(
    body: VegetationPlanRequest,
    current_user: CurrentUser,
    use_case: Annotated[
        GenerateVegetationPlanUseCase,
        Depends(provide_generate_vegetation_plan_use_case),
    ],
) -> AgentNarrativeSchema:
    """Characterize the city by lat/lon and propose staged planting for a neighborhood."""

    narrative = use_case.execute(
        VegetationPlanCommand(
            project_id=body.project_id,
            owner_id=current_user.id,
            city=CityLocation(
                name=body.city.name,
                latitude=body.city.latitude,
                longitude=body.city.longitude,
            ),
            focus=_to_snapshot(body.focus),
        )
    )
    return _to_schema(narrative)
