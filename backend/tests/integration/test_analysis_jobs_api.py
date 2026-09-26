"""API contract tests for analysis job lifecycle."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.analysis_jobs import (
    CancelAnalysisJobUseCase,
    CompleteAnalysisJobUseCase,
    CreateAnalysisJobUseCase,
    FailAnalysisJobUseCase,
    GetAnalysisJobUseCase,
    ListAnalysisJobsUseCase,
    StartAnalysisJobUseCase,
    UpdateAnalysisJobProgressUseCase,
)
from greencity.application.use_cases.aois import CreateAreaOfInterestUseCase
from greencity.application.use_cases.projects import CreateProjectUseCase
from greencity.application.use_cases.scoring_profiles import CreateScoringProfileUseCase
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
    app.dependency_overrides[deps.provide_create_scoring_profile_use_case] = (
        lambda: CreateScoringProfileUseCase(uow)
    )
    app.dependency_overrides[deps.provide_create_analysis_job_use_case] = (
        lambda: CreateAnalysisJobUseCase(uow)
    )
    app.dependency_overrides[deps.provide_get_analysis_job_use_case] = (
        lambda: GetAnalysisJobUseCase(uow)
    )
    app.dependency_overrides[deps.provide_list_analysis_jobs_use_case] = (
        lambda: ListAnalysisJobsUseCase(uow)
    )
    app.dependency_overrides[deps.provide_start_analysis_job_use_case] = (
        lambda: StartAnalysisJobUseCase(uow)
    )
    app.dependency_overrides[deps.provide_cancel_analysis_job_use_case] = (
        lambda: CancelAnalysisJobUseCase(uow)
    )
    app.dependency_overrides[deps.provide_update_analysis_job_progress_use_case] = (
        lambda: UpdateAnalysisJobProgressUseCase(uow)
    )
    app.dependency_overrides[deps.provide_complete_analysis_job_use_case] = (
        lambda: CompleteAnalysisJobUseCase(uow)
    )
    app.dependency_overrides[deps.provide_fail_analysis_job_use_case] = (
        lambda: FailAnalysisJobUseCase(uow)
    )
    return TestClient(app)


def _seed_refs(client: TestClient, headers: dict) -> tuple[str, str, str]:
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "Job Pilot", "description": "", "status": "active"},
    ).json()
    aoi = client.post(
        "/api/v1/areas-of-interest",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": "Boundary",
            "description": "",
            "geometry": SAMPLE_POLYGON,
            "kind": "city",
        },
    ).json()
    profile = client.post(
        "/api/v1/scoring-profiles",
        headers=headers,
        json={
            "name": "Balanced",
            "use_balanced_defaults": True,
        },
    ).json()
    return project["id"], aoi["id"], profile["id"]


def test_analysis_job_api_lifecycle(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="lifecycle@city.gov")
    project_id, aoi_id, profile_id = _seed_refs(client, headers)

    created = client.post(
        "/api/v1/analysis-jobs",
        headers=headers,
        json={
            "project_id": project_id,
            "aoi_id": aoi_id,
            "scoring_profile_id": profile_id,
        },
    )
    assert created.status_code == 201
    job = created.json()
    assert job["status"] == "queued"

    started = client.post(f"/api/v1/analysis-jobs/{job['id']}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    progress = client.patch(
        f"/api/v1/analysis-jobs/{job['id']}/progress",
        headers=headers,
        json={"current_step": "ranking", "progress_pct": 80},
    )
    assert progress.status_code == 200
    assert progress.json()["progress_pct"] == 80

    completed = client.post(f"/api/v1/analysis-jobs/{job['id']}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    listed = client.get(f"/api/v1/analysis-jobs?project_id={project_id}", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_invalid_transition_returns_409(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="conflict@city.gov")
    project_id, aoi_id, profile_id = _seed_refs(client, headers)
    job = client.post(
        "/api/v1/analysis-jobs",
        headers=headers,
        json={
            "project_id": project_id,
            "aoi_id": aoi_id,
            "scoring_profile_id": profile_id,
        },
    ).json()

    client.post(f"/api/v1/analysis-jobs/{job['id']}/cancel", headers=headers)
    again = client.post(f"/api/v1/analysis-jobs/{job['id']}/start", headers=headers)
    assert again.status_code == 409
