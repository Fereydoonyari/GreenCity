"""API contract tests for LangGraph analysis job run endpoint."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.analysis_jobs import CreateAnalysisJobUseCase
from greencity.application.use_cases.aois import CreateAreaOfInterestUseCase
from greencity.application.use_cases.orchestration import RunAnalysisOrchestrationUseCase
from greencity.application.use_cases.projects import CreateProjectUseCase
from greencity.application.use_cases.scoring_profiles import CreateScoringProfileUseCase
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import BoundingBox, OsmContext
from greencity.infrastructure.agent import LangGraphAnalysisOrchestrator
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
            roads=(),
            parks=(),
            buildings=(),
            total_road_length_m=3_000.0,
            total_park_area_m2=12_000.0,
            total_building_area_m2=30_000.0,
            aoi_area_m2=300_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )


class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.45


def _build_client(monkeypatch) -> tuple[TestClient, InMemoryUnitOfWork]:
    configure_test_jwt(monkeypatch)
    uow = InMemoryUnitOfWork()
    app = create_app()
    orchestrator = LangGraphAnalysisOrchestrator(uow, _StubOsm(), _StubParkAccess())

    app.dependency_overrides[deps.provide_unit_of_work] = lambda: uow
    install_auth_overrides(app, uow)
    app.dependency_overrides[deps.provide_create_project_use_case] = lambda: CreateProjectUseCase(
        uow
    )
    app.dependency_overrides[deps.provide_create_aoi_use_case] = (
        lambda: CreateAreaOfInterestUseCase(uow)
    )
    app.dependency_overrides[deps.provide_create_scoring_profile_use_case] = (
        lambda: CreateScoringProfileUseCase(uow)
    )
    app.dependency_overrides[deps.provide_create_analysis_job_use_case] = (
        lambda: CreateAnalysisJobUseCase(uow)
    )
    app.dependency_overrides[deps.provide_run_analysis_orchestration_use_case] = (
        lambda: RunAnalysisOrchestrationUseCase(uow, orchestrator)
    )
    return TestClient(app), uow


def test_run_analysis_job_api(monkeypatch) -> None:
    client, _uow = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="orch@city.gov")

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Agent Pilot", "description": "", "status": "active"},
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
    profile = client.post(
        "/api/v1/scoring-profiles",
        headers=headers,
        json={
            "name": "Default",
            "use_balanced_defaults": True,
            "is_default": True,
        },
    ).json()
    job = client.post(
        "/api/v1/analysis-jobs",
        headers=headers,
        json={
            "project_id": project["id"],
            "aoi_id": aoi["id"],
            "scoring_profile_id": profile["id"],
        },
    ).json()

    response = client.post(
        f"/api/v1/analysis-jobs/{job['id']}/run",
        headers=headers,
        json={"vegetation_coverage": 0.28, "green_area_m2": 6_000, "auto_start": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["job"]["progress_pct"] == 100
    assert body["analysis"]["indicators"]["vegetation_coverage"] == 0.28
    assert 0 <= body["analysis"]["green_deficiency_score"]["score"] <= 100
    assert "validate_inputs" in body["analysis"]["steps_completed"]
    assert body["analysis"]["report"] is not None
    assert body["analysis"]["summary"]
    assert len(body["analysis"]["report"]["drivers"]) == 4
