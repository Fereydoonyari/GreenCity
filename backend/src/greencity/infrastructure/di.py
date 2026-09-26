"""Dependency injection / composition root helpers.

Wires concrete adapters to use cases. Presentation depends on these
factories rather than constructing infrastructure types inline.
"""

from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from greencity import __version__
from greencity.application.use_cases.check_health import CheckHealthUseCase
from greencity.config import Settings, get_settings
from greencity.infrastructure.persistence.database import (
    DatabaseHealthAdapter,
    create_db_engine,
    create_session_factory,
)


@lru_cache
def get_engine() -> Engine:
    """Return a process-wide SQLAlchemy engine."""

    return create_db_engine(get_settings())


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return a process-wide session factory."""

    return create_session_factory(get_engine())


def get_check_health_use_case(settings: Settings | None = None) -> CheckHealthUseCase:
    """Compose the health-check use case with infrastructure adapters.

    Args:
        settings: Optional settings override (useful in tests).

    Returns:
        Configured ``CheckHealthUseCase``.
    """

    resolved = settings or get_settings()
    engine = create_db_engine(resolved) if settings is not None else get_engine()
    return CheckHealthUseCase(
        database_health=DatabaseHealthAdapter(engine),
        version=__version__,
    )
