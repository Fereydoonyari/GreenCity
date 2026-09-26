"""Health check use case.

Returns application and dependency readiness for liveness/readiness probes.
Belongs in the application layer because it coordinates ports without
exposing infrastructure types to the presentation layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from greencity.domain.ports.health import HealthCheckPort


@dataclass(frozen=True)
class HealthStatus:
    """Result of a health check use case."""

    status: str
    database: str
    version: str


class CheckHealthUseCase:
    """Evaluate overall system health via injected ports.

    Design: constructor injection of ``HealthCheckPort`` keeps the use case
    testable with fakes and free of SQLAlchemy/session details.
    """

    def __init__(self, database_health: HealthCheckPort, *, version: str) -> None:
        self._database_health = database_health
        self._version = version

    def execute(self) -> HealthStatus:
        """Run readiness checks and return a structured status.

        Returns:
            ``HealthStatus`` with overall status ``healthy`` or ``degraded``.
        """

        db_ok = self._database_health.is_ready()
        return HealthStatus(
            status="healthy" if db_ok else "degraded",
            database="up" if db_ok else "down",
            version=self._version,
        )
