"""Repository and unit-of-work ports for persistence."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.entities.aoi import AreaOfInterest
from greencity.domain.entities.project import Project
from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.domain.entities.user import User


class UserRepository(Protocol):
    """Persistence port for the User aggregate."""

    def add(self, user: User) -> User:
        """Insert a new user and return the persisted entity."""

        ...

    def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by id, or ``None`` if missing."""

        ...

    def get_by_email(self, email: str) -> User | None:
        """Return a user by normalized email, or ``None`` if missing."""

        ...

    def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        """Return a page of users ordered by creation time descending."""

        ...

    def save(self, user: User) -> User:
        """Persist mutations to an existing user."""

        ...

    def delete(self, user_id: UUID) -> bool:
        """Delete a user by id. Returns ``True`` if a row was removed."""

        ...


class ProjectRepository(Protocol):
    """Persistence port for the Project aggregate."""

    def add(self, project: Project) -> Project:
        """Insert a new project and return the persisted entity."""

        ...

    def get_by_id(self, project_id: UUID) -> Project | None:
        """Return a project by id, or ``None`` if missing."""

        ...

    def list(
        self,
        *,
        owner_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        """Return a page of projects, optionally filtered by owner."""

        ...

    def save(self, project: Project) -> Project:
        """Persist mutations to an existing project."""

        ...

    def delete(self, project_id: UUID) -> bool:
        """Delete a project by id. Returns ``True`` if a row was removed."""

        ...


class AreaOfInterestRepository(Protocol):
    """Persistence port for the AreaOfInterest aggregate."""

    def add(self, aoi: AreaOfInterest) -> AreaOfInterest:
        """Insert a new AOI and return the persisted entity."""

        ...

    def get_by_id(self, aoi_id: UUID) -> AreaOfInterest | None:
        """Return an AOI by id, or ``None`` if missing."""

        ...

    def list_by_project(
        self,
        project_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AreaOfInterest]:
        """Return AOIs for a project, newest first."""

        ...

    def save(self, aoi: AreaOfInterest) -> AreaOfInterest:
        """Persist mutations to an existing AOI."""

        ...

    def delete(self, aoi_id: UUID) -> bool:
        """Delete an AOI by id. Returns ``True`` if a row was removed."""

        ...


class ScoringProfileRepository(Protocol):
    """Persistence port for the ScoringProfile aggregate."""

    def add(self, profile: ScoringProfile) -> ScoringProfile:
        """Insert a new scoring profile and return the persisted entity."""

        ...

    def get_by_id(self, profile_id: UUID) -> ScoringProfile | None:
        """Return a scoring profile by id, or ``None`` if missing."""

        ...

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ScoringProfile]:
        """Return a page of scoring profiles, newest first."""

        ...

    def list_by_owner(
        self,
        owner_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ScoringProfile]:
        """Return scoring profiles owned by ``owner_id``."""

        ...

    def save(self, profile: ScoringProfile) -> ScoringProfile:
        """Persist mutations to an existing scoring profile."""

        ...

    def delete(self, profile_id: UUID) -> bool:
        """Delete a scoring profile by id. Returns ``True`` if removed."""

        ...


class AnalysisJobRepository(Protocol):
    """Persistence port for the AnalysisJob aggregate."""

    def add(self, job: AnalysisJob) -> AnalysisJob:
        """Insert a new analysis job and return the persisted entity."""

        ...

    def get_by_id(self, job_id: UUID) -> AnalysisJob | None:
        """Return an analysis job by id, or ``None`` if missing."""

        ...

    def list_by_project(
        self,
        project_id: UUID,
        *,
        status: AnalysisJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisJob]:
        """Return jobs for a project, newest first, optionally filtered by status."""

        ...

    def list_by_aoi(
        self,
        aoi_id: UUID,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AnalysisJob]:
        """Return jobs that reference an AOI, newest first."""

        ...

    def save(self, job: AnalysisJob) -> AnalysisJob:
        """Persist mutations to an existing analysis job."""

        ...

    def delete(self, job_id: UUID) -> bool:
        """Delete an analysis job by id. Returns ``True`` if removed."""

        ...


class AnalysisReportRepository(Protocol):
    """Persistence port for explainable analysis reports."""

    def add(self, report: AnalysisReport) -> AnalysisReport:
        """Insert a new report and return the persisted entity."""

        ...

    def get_by_id(self, report_id: UUID) -> AnalysisReport | None:
        """Return a report by id, or ``None`` if missing."""

        ...

    def get_by_job_id(self, job_id: UUID) -> AnalysisReport | None:
        """Return the latest report for an analysis job, if any."""

        ...

    def list_by_aoi(
        self,
        aoi_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisReport]:
        """Return reports for an AOI, newest first."""

        ...

    def delete(self, report_id: UUID) -> bool:
        """Delete a report by id. Returns ``True`` if removed."""

        ...


class UnitOfWork(Protocol):
    """Transactional boundary grouping repositories.

    Application use cases depend on this port so commits/rollbacks stay
    outside controllers while remaining independent of SQLAlchemy.
    """

    users: UserRepository
    projects: ProjectRepository
    areas_of_interest: AreaOfInterestRepository
    scoring_profiles: ScoringProfileRepository
    analysis_jobs: AnalysisJobRepository
    analysis_reports: AnalysisReportRepository

    def commit(self) -> None:
        """Persist all pending changes in the current transaction."""

        ...

    def rollback(self) -> None:
        """Discard pending changes in the current transaction."""

        ...
