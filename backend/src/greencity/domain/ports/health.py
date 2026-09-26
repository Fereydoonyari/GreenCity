"""Health-check port for infrastructure readiness probes."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class HealthCheckPort(Protocol):
    """Port for checking infrastructure readiness.

    Used by the health use case so presentation never talks to the
    database (or other adapters) directly.
    """

    def is_ready(self) -> bool:
        """Return ``True`` when the dependency is reachable and ready."""

        ...
