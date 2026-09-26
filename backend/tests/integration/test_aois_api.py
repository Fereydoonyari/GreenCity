"""API contract tests for areas of interest."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.aois import (
    CreateAreaOfInterestUseCase,
    DeleteAreaOfInterestUseCase,
    GetAreaOfInterestUseCase,
    ListAreasOfInterestUseCase,
    UpdateAreaOfInterestUseCase,
)
from greencity.application.use_cases.projects import CreateProjectUseCase
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
    app.dependency_overrides[deps.provide_get_aoi_use_case] = lambda: GetAreaOfInterestUseCase(uow)
    app.dependency_overrides[deps.provide_list_aois_use_case] = (
        lambda: ListAreasOfInterestUseCase(uow)
    )
    app.dependency_overrides[deps.provide_update_aoi_use_case] = (
        lambda: UpdateAreaOfInterestUseCase(uow)
    )
    app.dependency_overrides[deps.provide_delete_aoi_use_case] = (
        lambda: DeleteAreaOfInterestUseCase(uow)
    )
    return TestClient(app)


def test_aoi_api_flow(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="map@city.gov")

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Map Pilot", "description": "", "status": "active"},
    ).json()

    created = client.post(
        "/api/v1/areas-of-interest",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": "Central polygon",
            "description": "Drawn boundary",
            "geometry": SAMPLE_POLYGON,
            "kind": "city",
        },
    )
    assert created.status_code == 201
    aoi = created.json()
    assert aoi["geometry"]["type"] == "Polygon"
    assert aoi["kind"] == "city"

    listed = client.get(
        f"/api/v1/areas-of-interest?project_id={project['id']}",
        headers=headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/v1/areas-of-interest/{aoi['id']}",
        headers=headers,
        json={"name": "Central polygon v2"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Central polygon v2"

    deleted = client.delete(f"/api/v1/areas-of-interest/{aoi['id']}", headers=headers)
    assert deleted.status_code == 204


def test_aoi_rejects_invalid_geometry(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="badgeom@city.gov")
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Map Pilot", "description": "", "status": "active"},
    ).json()

    response = client.post(
        "/api/v1/areas-of-interest",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": "Point not allowed",
            "description": "",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        },
    )
    assert response.status_code == 422
