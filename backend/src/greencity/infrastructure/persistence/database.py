"""SQLAlchemy engine and session factory.

Database wiring lives here so use cases never construct engines themselves.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from greencity.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine from application settings.

    Args:
        settings: Application settings containing ``database_url``.

    Returns:
        Configured SQLAlchemy ``Engine``.
    """

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to ``engine``."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Commits on success; rolls back and re-raises on error.
    """

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DatabaseHealthAdapter:
    """``HealthCheckPort`` implementation using a simple ``SELECT 1``.

    Isolates SQLAlchemy from the application layer while still reporting
    real database connectivity for readiness probes.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_ready(self) -> bool:
        """Return ``True`` if the database accepts a trivial query."""

        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
