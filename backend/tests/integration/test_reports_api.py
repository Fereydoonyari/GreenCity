"""API contract tests for explainable reports."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.analysis_jobs import CreateAnalysisJobUseCase
from greencity.application.use_cases.aois import CreateAreaOfInterestUseCase
from greencity.application.use_cases.indicators import ComputeIndicatorsUseCase
from greencity.application.use_cases.orchestration import RunAnalysisOrchestrationUseCase
from greencity.application.use_cases.projects import CreateProjectUseCase
from greencity.application.use_cases.reports import (
    GenerateReportUseCase,
    GetReportByJobUseCase,
    GetReportUseCase,
)
from greencity.application.use_cases.scoring import ScoreAoiUseCase
from greencity.application.use_cases.scoring_profiles import CreateScoringProfileUseCase
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import BoundingBox, OsmContext
from greencity.infrastructure.agent import LangGraphAnalysisOrchestrator
from greencity.infrastructure.reporting import TemplateReportExplainer
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


def _build_client(monkeypatch) -> TestClient:
    configure_test_jwt(monkeypatch)
    uow = InMemoryUnitOfWork()
    app = create_app()
    explainer = TemplateReportExplainer()
    compute = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())
    score_aoi = ScoreAoiUseCase(uow, compute)
    orchestrator = LangGraphAnalysisOrchestrator(
        uow, _StubOsm(), _StubParkAccess(), explainer
    )

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
    app.dependency_overrides[deps.provide_generate_report_use_case] = (
        lambda: GenerateReportUseCase(uow, explainer, score_aoi)
    )
    app.dependency_overrides[deps.provide_get_report_use_case] = lambda: GetReportUseCase(uow)
    app.dependency_overrides[deps.provide_get_report_by_job_use_case] = (
        lambda: GetReportByJobUseCase(uow)
    )
    return TestClient(app)


def _seed_job(client: TestClient, headers: dict[str, str]) -> dict:
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Report Pilot", "description": "", "status": "active"},
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
    return client.post(
        "/api/v1/analysis-jobs",
        headers=headers,
        json={
            "project_id": project["id"],
            "aoi_id": aoi["id"],
            "scoring_profile_id": profile["id"],
        },
    ).json()


def test_generate_report_api(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="reports@city.gov")
    job = _seed_job(client, headers)

    response = client.post(
        "/api/v1/reports",
        headers=headers,
        json={
            "analysis_job_id": job["id"],
            "vegetation_coverage": 0.25,
            "green_area_m2": 7_000,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["analysis_job_id"] == job["id"]
    assert len(body["drivers"]) == 4
    assert body["recommendations"]
    assert "methodology_notes" in body

    by_id = client.get(f"/api/v1/reports/{body['id']}", headers=headers)
    assert by_id.status_code == 200
    by_job = client.get(f"/api/v1/analysis-jobs/{job['id']}/report", headers=headers)
    assert by_job.status_code == 200
    assert by_job.json()["id"] == body["id"]


def test_orchestration_includes_report(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="orch-report@city.gov")
    job = _seed_job(client, headers)

    response = client.post(
        f"/api/v1/analysis-jobs/{job['id']}/run",
        headers=headers,
        json={"vegetation_coverage": 0.28, "green_area_m2": 6_000, "auto_start": True},
    )
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["report"] is not None
    assert analysis["report"]["headline"]
    assert "Green Deficiency Score" in analysis["summary"] or analysis["summary"]
    assert len(analysis["report"]["drivers"]) == 4
