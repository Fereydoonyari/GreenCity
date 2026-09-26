"""API integration tests using FastAPI TestClient (no live database required)."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.check_health import HealthStatus
from greencity.main import create_app
from greencity.presentation.dependencies import provide_check_health_use_case


class StubCheckHealthUseCase:
    """Stub that bypasses real DB connectivity for API contract tests."""

    def execute(self) -> HealthStatus:
        return HealthStatus(status="healthy", database="up", version="0.1.0")


def test_health_endpoint_returns_expected_payload() -> None:
    """GET /api/v1/health returns the use-case result as JSON."""

    app = create_app()
    app.dependency_overrides[provide_check_health_use_case] = StubCheckHealthUseCase

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "up",
        "version": "0.1.0",
    }


def test_root_returns_service_metadata() -> None:
    """GET / returns basic service discovery hints."""

    client = TestClient(create_app())
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert "name" in payload
    assert payload["health"] == "/api/v1/health"
