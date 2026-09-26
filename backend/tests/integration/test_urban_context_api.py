"""API contract tests for urban-context (OSM) endpoints."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.aois import CreateAreaOfInterestUseCase
from greencity.application.use_cases.projects import CreateProjectUseCase
from greencity.application.use_cases.urban_context import FetchOsmContextUseCase
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import BoundingBox, OsmContext, OsmRoad
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
                    osm_id=9,
                    highway="primary",
                    length_m=250.0,
                    geometry={"type": "LineString", "coordinates": [[2.35, 48.85], [2.36, 48.85]]},
                ),
            ),
            parks=(),
            buildings=(),
            total_road_length_m=250.0,
            total_park_area_m2=0.0,
            total_building_area_m2=0.0,
            aoi_area_m2=500_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )


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
    app.dependency_overrides[deps.provide_fetch_osm_context_use_case] = (
        lambda: FetchOsmContextUseCase(uow, _StubOsm())
    )
    return TestClient(app)


def test_urban_context_api(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="osm@city.gov")

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "OSM Pilot", "description": "", "status": "active"},
    ).json()
    aoi = client.post(
        "/api/v1/areas-of-interest",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": "Neighbourhood",
            "geometry": SAMPLE_POLYGON,
            "kind": "city",
        },
    ).json()

    osm = client.get(f"/api/v1/urban-context/aois/{aoi['id']}/osm", headers=headers)
    assert osm.status_code == 200
    body = osm.json()
    assert body["road_count"] == 1
    assert body["total_road_length_m"] == 250.0
    assert body["roads"][0]["highway"] == "primary"


def test_urban_context_aoi_not_found(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="missing@city.gov")
    missing = "00000000-0000-0000-0000-000000000001"
    assert client.get(
        f"/api/v1/urban-context/aois/{missing}/osm",
        headers=headers,
    ).status_code == 404
