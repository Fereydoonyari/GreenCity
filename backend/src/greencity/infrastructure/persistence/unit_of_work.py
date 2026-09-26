"""SQLAlchemy unit of work implementing the domain ``UnitOfWork`` port."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from greencity.infrastructure.persistence.repositories import (
    SqlAlchemyAnalysisJobRepository,
    SqlAlchemyAnalysisReportRepository,
    SqlAlchemyAreaOfInterestRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyScoringProfileRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyUnitOfWork:
    """Transactional unit of work wrapping a SQLAlchemy session.

    Supports context-manager usage::

        with SqlAlchemyUnitOfWork(session_factory) as uow:
            uow.users.add(...)
            uow.commit()
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None
        self.users: SqlAlchemyUserRepository
        self.projects: SqlAlchemyProjectRepository
        self.areas_of_interest: SqlAlchemyAreaOfInterestRepository
        self.scoring_profiles: SqlAlchemyScoringProfileRepository
        self.analysis_jobs: SqlAlchemyAnalysisJobRepository
        self.analysis_reports: SqlAlchemyAnalysisReportRepository

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self.session)
        self.projects = SqlAlchemyProjectRepository(self.session)
        self.areas_of_interest = SqlAlchemyAreaOfInterestRepository(self.session)
        self.scoring_profiles = SqlAlchemyScoringProfileRepository(self.session)
        self.analysis_jobs = SqlAlchemyAnalysisJobRepository(self.session)
        self.analysis_reports = SqlAlchemyAnalysisReportRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        if self.session is not None:
            self.session.close()

    def commit(self) -> None:
        """Commit the current session transaction."""

        if self.session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self.session.commit()

    def rollback(self) -> None:
        """Roll back the current session transaction."""

        if self.session is not None:
            self.session.rollback()
