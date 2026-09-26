"""API contract tests for scoring profiles."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileUseCase,
    DeleteScoringProfileUseCase,
    GetScoringProfileUseCase,
    ListScoringProfilesUseCase,
    UpdateScoringProfileUseCase,
)
from greencity.main import create_app
from greencity.presentation import dependencies as deps
from tests.auth_helpers import (
    configure_test_jwt,
    install_auth_overrides,
    register_and_auth_headers,
)
from tests.fakes import InMemoryUnitOfWork


def _build_client(monkeypatch) -> TestClient:
    configure_test_jwt(monkeypatch)
    uow = InMemoryUnitOfWork()
    app = create_app()
    app.dependency_overrides[deps.provide_unit_of_work] = lambda: uow
    install_auth_overrides(app, uow)
    app.dependency_overrides[deps.provide_create_scoring_profile_use_case] = (
        lambda: CreateScoringProfileUseCase(uow)
    )
    app.dependency_overrides[deps.provide_get_scoring_profile_use_case] = (
        lambda: GetScoringProfileUseCase(uow)
    )
    app.dependency_overrides[deps.provide_list_scoring_profiles_use_case] = (
        lambda: ListScoringProfilesUseCase(uow)
    )
    app.dependency_overrides[deps.provide_update_scoring_profile_use_case] = (
        lambda: UpdateScoringProfileUseCase(uow)
    )
    app.dependency_overrides[deps.provide_delete_scoring_profile_use_case] = (
        lambda: DeleteScoringProfileUseCase(uow)
    )
    return TestClient(app)


def test_scoring_profile_api_flow(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="weights@city.gov")

    created = client.post(
        "/api/v1/scoring-profiles",
        headers=headers,
        json={
            "name": "Balanced",
            "description": "Default blend",
            "use_balanced_defaults": True,
            "is_default": True,
        },
    )
    assert created.status_code == 201
    profile = created.json()
    assert profile["weights"]["vegetation_coverage"] == 0.25
    assert profile["is_default"] is True

    listed = client.get("/api/v1/scoring-profiles", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/v1/scoring-profiles/{profile['id']}",
        headers=headers,
        json={"name": "Vegetation-heavy"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Vegetation-heavy"

    deleted = client.delete(f"/api/v1/scoring-profiles/{profile['id']}", headers=headers)
    assert deleted.status_code == 204


def test_scoring_profile_rejects_bad_weight_sum(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="badweights@city.gov")

    response = client.post(
        "/api/v1/scoring-profiles",
        headers=headers,
        json={
            "name": "Broken",
            "weights": {
                "vegetation_coverage": 0.5,
                "green_area_per_m2": 0.5,
                "road_density": 0.5,
                "built_up_ratio": 0.0,
            },
        },
    )
    assert response.status_code == 422
