"""Unit tests for CheckHealthUseCase."""

from greencity.application.use_cases.check_health import CheckHealthUseCase


class FakeHealthyDatabase:
    """Fake HealthCheckPort that always reports ready."""

    def is_ready(self) -> bool:
        return True


class FakeUnhealthyDatabase:
    """Fake HealthCheckPort that always reports not ready."""

    def is_ready(self) -> bool:
        return False


def test_check_health_returns_healthy_when_database_is_up() -> None:
    """Healthy DB → overall status healthy."""

    use_case = CheckHealthUseCase(FakeHealthyDatabase(), version="0.1.0")
    result = use_case.execute()

    assert result.status == "healthy"
    assert result.database == "up"
    assert result.version == "0.1.0"


def test_check_health_returns_degraded_when_database_is_down() -> None:
    """Down DB → overall status degraded."""

    use_case = CheckHealthUseCase(FakeUnhealthyDatabase(), version="0.1.0")
    result = use_case.execute()

    assert result.status == "degraded"
    assert result.database == "down"
