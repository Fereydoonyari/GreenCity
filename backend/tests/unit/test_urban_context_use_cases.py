"""Unit tests for OSM urban-context use cases."""

from __future__ import annotations

from uuid import uuid4

import pytest

from greencity.application.use_cases.aois import CreateAreaOfInterestCommand, CreateAreaOfInterestUseCase
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.urban_context import (
    FetchOsmContextCommand,
    FetchOsmContextUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.exceptions import NotFoundError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
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
                    length_m=100.0,
                    geometry={"type": "LineString", "coordinates": [[2.35, 48.85], [2.36, 48.85]]},
                ),
            ),
            parks=(),
            buildings=(),
            total_road_length_m=100.0,
            total_park_area_m2=0.0,
            total_building_area_m2=0.0,
            aoi_area_m2=1_000_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )


def _seed_aoi(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="u@example.com", full_name="U", password="secret123")
    )
    project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="P", description="", owner_id=user.id)
    )
    aoi = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="A",
            description="",
            geometry=SAMPLE,
        )
    )
    return aoi


def test_fetch_osm_context_use_case() -> None:
    uow = InMemoryUnitOfWork()
    aoi = _seed_aoi(uow)
    uc = FetchOsmContextUseCase(uow, _StubOsm())
    ctx = uc.execute(FetchOsmContextCommand(aoi_id=aoi.id))
    assert len(ctx.roads) == 1
    assert ctx.total_road_length_m == pytest.approx(100.0)


def test_fetch_osm_not_found() -> None:
    uow = InMemoryUnitOfWork()
    uc = FetchOsmContextUseCase(uow, _StubOsm())
    with pytest.raises(NotFoundError):
        uc.execute(FetchOsmContextCommand(aoi_id=uuid4()))
