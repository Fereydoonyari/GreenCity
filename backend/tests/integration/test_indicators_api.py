"""API contract tests for indicator computation."""

import pytest
from fastapi.testclient import TestClient

from greencity.application.use_cases.aois import CreateAreaOfInterestUseCase
from greencity.application.use_cases.indicators import ComputeIndicatorsUseCase
from greencity.application.use_cases.projects import CreateProjectUseCase
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
    OsmPark,
    OsmRoad,
)
from greencity.main import create_app
from greencity.presentation import dependencies as deps
from tests.auth_helpers import (
    configure_test_jwt,
    install_auth_overrides,
    register_and_auth_headers,
)
from tests.fakes import InMemoryUnitOfWork

SAMPLE_POLYGON = {
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
                    highway="primary",
                    length_m=500.0,
                    geometry={"type": "LineString", "coordinates": [[2.35, 48.85], [2.36, 48.85]]},
                ),
            ),
            parks=(
                OsmPark(
                    osm_id=2,
                    name="Park",
                    area_m2=25_000.0,
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
            total_road_length_m=500.0,
            total_park_area_m2=25_000.0,
            total_building_area_m2=0.0,
            aoi_area_m2=250_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )



class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.55


def _build_client(monkeypatch) -> TestClient:
    configure_test_jwt(monkeypatch)
    uow = InMemoryUnitOfWork()
    app = create_app()

    app.dependency_overrides[deps.provide_unit_of_work] = lambda: uow
    install_auth_overrides(app, uow)
    app.dependency_overrides[deps.provide_create_project_use_case] = lambda: CreateProjectUseCase(
        uow
    )
    app.dependency_overrides[deps.provide_create_aoi_use_case] = (
        lambda: CreateAreaOfInterestUseCase(uow)
    )
    app.dependency_overrides[deps.provide_compute_indicators_use_case] = (
        lambda: ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    )
    return TestClient(app)


def test_compute_indicators_api(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="ind@city.gov")

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Indicators", "description": "", "status": "active"},
    ).json()
    aoi = client.post(
        "/api/v1/areas-of-interest",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": "Zone",
            "geometry": SAMPLE_POLYGON,
            "kind": "city",
        },
    ).json()

    response = client.post(
        f"/api/v1/indicators/aois/{aoi['id']}/compute",
        headers=headers,
        json={"vegetation_coverage": 0.42, "green_area_m2": 15_000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["aoi_id"] == aoi["id"]
    assert body["indicators"]["vegetation_coverage"] == 0.42
    assert body["indicators"]["green_area_per_m2"] == pytest.approx(15_000 / 250_000)
    assert "park_accessibility" not in body["indicators"]
    assert "population_density" not in body["indicators"]
    assert "green_area_per_capita" not in body["indicators"]
    assert body["vegetation_source"] == "provided"
    assert body["park_count"] == 1
    assert body["road_count"] == 1


def test_compute_indicators_not_found(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    missing = "00000000-0000-0000-0000-000000000001"
    response = client.post(f"/api/v1/indicators/aois/{missing}/compute", json={})
    assert response.status_code == 404
