"""Auth API tests using in-memory fakes."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.auth import LoginUserUseCase, RegisterUserUseCase
from greencity.application.use_cases.users import CreateUserUseCase
from greencity.config import get_settings
from greencity.infrastructure.security.tokens import JwtAccessTokenService
from greencity.main import create_app
from greencity.presentation import dependencies as deps
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork


def _build_client() -> tuple[TestClient, InMemoryUnitOfWork]:
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
    # Current user resolution uses the real provider against overridden UoW + token secret.
    get_settings.cache_clear()
    return TestClient(app), uow


def test_register_login_me_flow(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "test-secret-greencity-jwt-key-32b")
    get_settings.cache_clear()
    client, _uow = _build_client()

    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": "planner@city.gov",
            "full_name": "City Planner",
            "password": "secret123",
        },
    )
    assert register.status_code == 201
    body = register.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "planner@city.gov"
    token = body["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "planner@city.gov"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "planner@city.gov", "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["full_name"] == "City Planner"

    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "planner@city.gov", "password": "wrong-pass"},
    )
    assert bad.status_code == 401
