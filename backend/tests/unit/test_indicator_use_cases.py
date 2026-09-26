"""Unit tests for ComputeIndicatorsUseCase."""

from __future__ import annotations

from uuid import uuid4

import pytest

from greencity.application.use_cases.aois import CreateAreaOfInterestCommand, CreateAreaOfInterestUseCase
from greencity.application.use_cases.indicators import (
    ComputeIndicatorsCommand,
    ComputeIndicatorsUseCase,
)
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
    OsmPark,
    OsmRoad,
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
            roads=(
                OsmRoad(
                    osm_id=1,
                    highway="residential",
                    length_m=1_000.0,
                    geometry={"type": "LineString", "coordinates": [[2.35, 48.85], [2.36, 48.85]]},
                ),
            ),
            parks=(
                OsmPark(
                    osm_id=2,
                    name="Park",
                    area_m2=50_000.0,
                    geometry={
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [2.352, 48.852],
                                [2.354, 48.852],
                                [2.354, 48.854],
                                [2.352, 48.854],
                                [2.352, 48.852],
                            ]
                        ],
                    },
                ),
            ),
            buildings=(),
            total_road_length_m=1_000.0,
            total_park_area_m2=50_000.0,
            total_building_area_m2=0.0,
            aoi_area_m2=500_000.0,  # 0.5 km²
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )



class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.6


def _seed_aoi(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="ind@example.com", full_name="I", password="secret123")
    )
    project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="P", description="", owner_id=user.id)
    )
    return CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="A",
            description="",
            geometry=SAMPLE,
        )
    )


def test_compute_with_proxies() -> None:
    uow = InMemoryUnitOfWork()
    aoi = _seed_aoi(uow)
    uc = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    result = uc.execute(ComputeIndicatorsCommand(aoi_id=aoi.id))

    assert result.vegetation_source == "osm_park_coverage_proxy"
    assert result.green_area_source == "osm_park_area"
    assert result.indicators.road_density == pytest.approx(2_000.0)  # 1000m / 0.5km²
    assert result.indicators.green_area_per_m2 == pytest.approx(50_000 / 500_000)
    assert not hasattr(result.indicators, "park_accessibility")
    assert not hasattr(result.indicators, "population_density")
    assert not hasattr(result.indicators, "green_area_per_capita")


def test_compute_with_provided_vegetation() -> None:
    uow = InMemoryUnitOfWork()
    aoi = _seed_aoi(uow)
    uc = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    result = uc.execute(
        ComputeIndicatorsCommand(
            aoi_id=aoi.id,
            vegetation_coverage=0.33,
            green_area_m2=12_000,
        )
    )
    assert result.vegetation_source == "provided"
    assert result.green_area_source == "provided"
    assert result.indicators.vegetation_coverage == pytest.approx(0.33)
    assert result.indicators.green_area_per_m2 == pytest.approx(12_000 / 500_000)


def test_not_found() -> None:
    uow = InMemoryUnitOfWork()
    uc = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    with pytest.raises(NotFoundError):
        uc.execute(ComputeIndicatorsCommand(aoi_id=uuid4()))


def test_invalid_walk_distance() -> None:
    uow = InMemoryUnitOfWork()
    aoi = _seed_aoi(uow)
    uc = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    with pytest.raises(ValidationError):
        uc.execute(ComputeIndicatorsCommand(aoi_id=aoi.id, park_walk_distance_m=0))
