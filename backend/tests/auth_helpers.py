"""Shared helpers for authenticated API integration tests."""

from __future__ import annotations

from greencity.application.use_cases.auth import LoginUserUseCase, RegisterUserUseCase
from greencity.application.use_cases.users import CreateUserUseCase
from greencity.config import get_settings
from greencity.infrastructure.security.tokens import JwtAccessTokenService
from greencity.presentation import dependencies as deps
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork


TEST_JWT_SECRET = "test-secret-greencity-jwt-key-32b"


def install_auth_overrides(app, uow: InMemoryUnitOfWork, hasher: FakePasswordHasher | None = None):
    """Wire register/login against the in-memory UoW and shared test JWT secret."""

    hasher = hasher or FakePasswordHasher()
    tokens = JwtAccessTokenService(secret=TEST_JWT_SECRET, expire_minutes=60)
    app.dependency_overrides[deps.provide_create_user_use_case] = lambda: CreateUserUseCase(
        uow, hasher
    )
    app.dependency_overrides[deps.provide_register_user_use_case] = lambda: RegisterUserUseCase(
        CreateUserUseCase(uow, hasher), tokens
    )
    app.dependency_overrides[deps.provide_login_user_use_case] = lambda: LoginUserUseCase(
        uow, hasher, tokens
    )
    return tokens


def configure_test_jwt(monkeypatch) -> None:
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    get_settings.cache_clear()


def register_and_auth_headers(client, *, email: str = "planner@city.gov") -> tuple[dict, dict]:
    """Register a user and return ``(user_json, auth_headers)``."""

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "City Planner",
            "password": "secret123",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    return body["user"], headers
