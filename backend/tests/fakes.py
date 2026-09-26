"""In-memory fakes for repository / unit-of-work ports (unit tests)."""

from __future__ import annotations

from uuid import UUID

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.entities.aoi import AreaOfInterest
from greencity.domain.entities.project import Project
from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.domain.entities.user import User


class InMemoryUserRepository:
    """Dict-backed ``UserRepository`` for unit tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, User] = {}

    def add(self, user: User) -> User:
        self._items[user.id] = user
        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._items.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        for user in self._items.values():
            if user.email == normalized:
                return user
        return None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        ordered = sorted(self._items.values(), key=lambda u: u.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def save(self, user: User) -> User:
        self._items[user.id] = user
        return user

    def delete(self, user_id: UUID) -> bool:
        return self._items.pop(user_id, None) is not None


class InMemoryProjectRepository:
    """Dict-backed ``ProjectRepository`` for unit tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, Project] = {}

    def add(self, project: Project) -> Project:
        self._items[project.id] = project
        return project

    def get_by_id(self, project_id: UUID) -> Project | None:
        return self._items.get(project_id)

    def list(
        self,
        *,
        owner_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        values = list(self._items.values())
        if owner_id is not None:
            values = [p for p in values if p.owner_id == owner_id]
        ordered = sorted(values, key=lambda p: p.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def save(self, project: Project) -> Project:
        self._items[project.id] = project
        return project

    def delete(self, project_id: UUID) -> bool:
        return self._items.pop(project_id, None) is not None


class InMemoryAreaOfInterestRepository:
    """Dict-backed ``AreaOfInterestRepository`` for unit tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, AreaOfInterest] = {}

    def add(self, aoi: AreaOfInterest) -> AreaOfInterest:
        self._items[aoi.id] = aoi
        return aoi

    def get_by_id(self, aoi_id: UUID) -> AreaOfInterest | None:
        return self._items.get(aoi_id)

    def list_by_project(
        self,
        project_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AreaOfInterest]:
        values = [a for a in self._items.values() if a.project_id == project_id]
        ordered = sorted(values, key=lambda a: a.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def save(self, aoi: AreaOfInterest) -> AreaOfInterest:
        self._items[aoi.id] = aoi
        return aoi

    def delete(self, aoi_id: UUID) -> bool:
        return self._items.pop(aoi_id, None) is not None


class InMemoryScoringProfileRepository:
    """Dict-backed ``ScoringProfileRepository`` for unit tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, ScoringProfile] = {}

    def add(self, profile: ScoringProfile) -> ScoringProfile:
        self._items[profile.id] = profile
        return profile

    def get_by_id(self, profile_id: UUID) -> ScoringProfile | None:
        return self._items.get(profile_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ScoringProfile]:
        ordered = sorted(self._items.values(), key=lambda p: p.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def list_by_owner(
        self,
        owner_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ScoringProfile]:
        values = [p for p in self._items.values() if p.owner_id == owner_id]
        ordered = sorted(values, key=lambda p: p.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def save(self, profile: ScoringProfile) -> ScoringProfile:
        self._items[profile.id] = profile
        return profile

    def delete(self, profile_id: UUID) -> bool:
        return self._items.pop(profile_id, None) is not None


class InMemoryAnalysisJobRepository:
    """Dict-backed ``AnalysisJobRepository`` for unit tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, AnalysisJob] = {}

    def add(self, job: AnalysisJob) -> AnalysisJob:
        self._items[job.id] = job
        return job

    def get_by_id(self, job_id: UUID) -> AnalysisJob | None:
        return self._items.get(job_id)

    def list_by_project(
        self,
        project_id: UUID,
        *,
        status: AnalysisJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisJob]:
        values = [j for j in self._items.values() if j.project_id == project_id]
        if status is not None:
            values = [j for j in values if j.status == status]
        ordered = sorted(values, key=lambda j: j.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def list_by_aoi(
        self,
        aoi_id: UUID,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AnalysisJob]:
        values = [j for j in self._items.values() if j.aoi_id == aoi_id]
        ordered = sorted(values, key=lambda j: j.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def save(self, job: AnalysisJob) -> AnalysisJob:
        self._items[job.id] = job
        return job

    def delete(self, job_id: UUID) -> bool:
        return self._items.pop(job_id, None) is not None


class InMemoryAnalysisReportRepository:
    """Dict-backed ``AnalysisReportRepository`` for unit tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, AnalysisReport] = {}

    def add(self, report: AnalysisReport) -> AnalysisReport:
        for existing in list(self._items.values()):
            if existing.analysis_job_id == report.analysis_job_id:
                self._items.pop(existing.id, None)
                break
        self._items[report.id] = report
        return report

    def get_by_id(self, report_id: UUID) -> AnalysisReport | None:
        return self._items.get(report_id)

    def get_by_job_id(self, job_id: UUID) -> AnalysisReport | None:
        matches = [r for r in self._items.values() if r.analysis_job_id == job_id]
        if not matches:
            return None
        return sorted(matches, key=lambda r: r.created_at, reverse=True)[0]

    def list_by_aoi(
        self,
        aoi_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisReport]:
        values = [r for r in self._items.values() if r.aoi_id == aoi_id]
        ordered = sorted(values, key=lambda r: r.created_at, reverse=True)
        return ordered[offset : offset + limit]

    def delete(self, report_id: UUID) -> bool:
        return self._items.pop(report_id, None) is not None


class InMemoryUnitOfWork:
    """In-memory ``UnitOfWork`` with commit/rollback no-ops for unit tests."""

    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.projects = InMemoryProjectRepository()
        self.areas_of_interest = InMemoryAreaOfInterestRepository()
        self.scoring_profiles = InMemoryScoringProfileRepository()
        self.analysis_jobs = InMemoryAnalysisJobRepository()
        self.analysis_reports = InMemoryAnalysisReportRepository()
        self.committed = False

    def __enter__(self) -> InMemoryUnitOfWork:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


class FakePasswordHasher:
    """Deterministic hasher for tests (not secure)."""

    def hash(self, plain_password: str) -> str:
        return f"hashed:{plain_password}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{plain_password}"
