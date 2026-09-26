"""Unit tests for scoring use cases."""

from __future__ import annotations

from uuid import uuid4

import pytest

from greencity.application.use_cases.aois import CreateAreaOfInterestCommand, CreateAreaOfInterestUseCase
from greencity.application.use_cases.indicators import ComputeIndicatorsUseCase
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.scoring import (
    RankItemInput,
    RankNeighborhoodsCommand,
    RankNeighborhoodsUseCase,
    ScoreAoiCommand,
    ScoreAoiUseCase,
)
from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileCommand,
    CreateScoringProfileUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
)
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork

SAMPLE = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.35, 48.85],
            [2.36, 48.85],
            [2.36, 48.86],
            [2.35, 48.86],
            [2.35, 48.85],
        ]
    ],
}


class _StubOsm:
    def fetch(self, geometry: GeoJsonGeometry) -> OsmContext:
        return OsmContext(
            roads=(),
            parks=(),
            buildings=(),
            total_road_length_m=5_000.0,
            total_park_area_m2=10_000.0,
            total_building_area_m2=50_000.0,
            aoi_area_m2=500_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )



class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.4


def _seed(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="score@example.com", full_name="S", password="secret123")
    )
    project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="P", description="", owner_id=user.id)
    )
    aoi = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id, name="A", description="", geometry=SAMPLE
        )
    )
    profile = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=user.id,
            name="Balanced",
            description="",
            use_balanced_defaults=True,
            is_default=True,
        )
    )
    return aoi, profile


def test_score_aoi_use_case() -> None:
    uow = InMemoryUnitOfWork()
    aoi, profile = _seed(uow)
    compute = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    uc = ScoreAoiUseCase(uow, compute)
    result = uc.execute(
        ScoreAoiCommand(
            aoi_id=aoi.id,
            scoring_profile_id=profile.id,
            vegetation_coverage=0.3,
            green_area_m2=8_000,
        )
    )
    assert 0 <= result.score.score <= 100
    assert result.indicators.vegetation_coverage == pytest.approx(0.3)
    assert result.vegetation_source == "provided"


def test_score_aoi_missing_profile() -> None:
    uow = InMemoryUnitOfWork()
    aoi, _ = _seed(uow)
    compute = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    uc = ScoreAoiUseCase(uow, compute)
    with pytest.raises(NotFoundError):
        uc.execute(ScoreAoiCommand(aoi_id=aoi.id, scoring_profile_id=uuid4()))


def test_rank_neighborhoods_use_case() -> None:
    uow = InMemoryUnitOfWork()
    _, profile = _seed(uow)
    uc = RankNeighborhoodsUseCase(uow)
    rankings = uc.execute(
        RankNeighborhoodsCommand(
            scoring_profile_id=profile.id,
            items=(
                RankItemInput(
                    id="n1",
                    label="North",
                    indicators=IndicatorValues(0.8, 0.4, 2_000.0, 0.1),
                ),
                RankItemInput(
                    id="n2",
                    label="South",
                    indicators=IndicatorValues(0.1, 0.05, 18_000.0, 0.9),
                ),
            ),
        )
    )
    assert rankings[0].id == "n2"
    assert rankings[0].rank == 1


def test_rank_rejects_empty() -> None:
    uow = InMemoryUnitOfWork()
    _, profile = _seed(uow)
    uc = RankNeighborhoodsUseCase(uow)
    with pytest.raises(ValidationError):
        uc.execute(RankNeighborhoodsCommand(scoring_profile_id=profile.id, items=()))
