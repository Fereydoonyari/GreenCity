"""API contract tests for users and projects using in-memory fakes."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.auth import LoginUserUseCase, RegisterUserUseCase
from greencity.application.use_cases.projects import (
    CreateProjectUseCase,
    DeleteProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
    UpdateProjectUseCase,
)
from greencity.application.use_cases.users import (
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from greencity.config import get_settings
from greencity.infrastructure.security.tokens import JwtAccessTokenService
from greencity.main import create_app
from greencity.presentation import dependencies as deps
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork


def _build_client() -> tuple[TestClient, InMemoryUnitOfWork, JwtAccessTokenService]:
    uow = InMemoryUnitOfWork()
    hasher = FakePasswordHasher()
    tokens = JwtAccessTokenService(secret="test-secret-greencity-jwt-key-32b", expire_minutes=60)
    app = create_app()

    app.dependency_overrides[deps.provide_unit_of_work] = lambda: uow
    app.dependency_overrides[deps.provide_create_user_use_case] = lambda: CreateUserUseCase(
        uow, hasher
    )
    app.dependency_overrides[deps.provide_register_user_use_case] = lambda: RegisterUserUseCase(
        CreateUserUseCase(uow, hasher), tokens
    )
    app.dependency_overrides[deps.provide_login_user_use_case] = lambda: LoginUserUseCase(
        uow, hasher, tokens
    )
    app.dependency_overrides[deps.provide_get_user_use_case] = lambda: GetUserUseCase(uow)
    app.dependency_overrides[deps.provide_list_users_use_case] = lambda: ListUsersUseCase(uow)
    app.dependency_overrides[deps.provide_update_user_use_case] = lambda: UpdateUserUseCase(uow)
    app.dependency_overrides[deps.provide_delete_user_use_case] = lambda: DeleteUserUseCase(uow)
    app.dependency_overrides[deps.provide_create_project_use_case] = lambda: CreateProjectUseCase(
        uow
    )
    app.dependency_overrides[deps.provide_get_project_use_case] = lambda: GetProjectUseCase(uow)
    app.dependency_overrides[deps.provide_list_projects_use_case] = lambda: ListProjectsUseCase(
        uow
    )
    app.dependency_overrides[deps.provide_update_project_use_case] = lambda: UpdateProjectUseCase(
        uow
    )
    app.dependency_overrides[deps.provide_delete_project_use_case] = lambda: DeleteProjectUseCase(
        uow
    )

    return TestClient(app), uow, tokens


def test_user_and_project_api_flow(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-greencity-jwt-key-32b")
    get_settings.cache_clear()
    client, _uow, _tokens = _build_client()

    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "planner@city.gov",
            "full_name": "City Planner",
            "password": "secret123",
        },
    )
    assert register.status_code == 201
    user = register.json()["user"]
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": "Downtown Greening",
            "description": "Pilot AOI later",
            "status": "active",
        },
    )
    assert create_project.status_code == 201
    project = create_project.json()
    assert project["owner_id"] == user["id"]
    assert project["status"] == "active"

    listed = client.get("/api/v1/projects", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Downtown Greening"
