"""SQLAlchemy implementations of persistence repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.entities.aoi import AreaOfInterest
from greencity.domain.entities.project import Project
from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.domain.entities.user import User
from greencity.infrastructure.persistence.mappers import (
    analysis_job_to_domain,
    analysis_report_to_domain,
    aoi_to_domain,
    apply_analysis_job_to_model,
    apply_analysis_report_to_model,
    apply_aoi_to_model,
    apply_project_to_model,
    apply_scoring_profile_to_model,
    apply_user_to_model,
    project_to_domain,
    scoring_profile_to_domain,
    user_to_domain,
)
from greencity.infrastructure.persistence.models import (
    AnalysisJobModel,
    AnalysisReportModel,
    AreaOfInterestModel,
    ProjectModel,
    ScoringProfileModel,
    UserModel,
)


class SqlAlchemyUserRepository:
    """``UserRepository`` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        model = UserModel()
        apply_user_to_model(user, model)
        self._session.add(model)
        self._session.flush()
        return user_to_domain(model)

    def get_by_id(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        return user_to_domain(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        statement = select(UserModel).where(UserModel.email == email.strip().lower())
        model = self._session.scalar(statement)
        return user_to_domain(model) if model else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        statement = (
            select(UserModel)
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [user_to_domain(m) for m in self._session.scalars(statement).all()]

    def save(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        if model is None:
            model = UserModel()
            self._session.add(model)
        apply_user_to_model(user, model)
        self._session.flush()
        return user_to_domain(model)

    def delete(self, user_id: UUID) -> bool:
        model = self._session.get(UserModel, user_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True


class SqlAlchemyProjectRepository:
    """``ProjectRepository`` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, project: Project) -> Project:
        model = ProjectModel()
        apply_project_to_model(project, model)
        self._session.add(model)
        self._session.flush()
        return project_to_domain(model)

    def get_by_id(self, project_id: UUID) -> Project | None:
        model = self._session.get(ProjectModel, project_id)
        return project_to_domain(model) if model else None

    def list(
        self,
        *,
        owner_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        statement = select(ProjectModel).order_by(ProjectModel.created_at.desc())
        if owner_id is not None:
            statement = statement.where(ProjectModel.owner_id == owner_id)
        statement = statement.limit(limit).offset(offset)
        return [project_to_domain(m) for m in self._session.scalars(statement).all()]

    def save(self, project: Project) -> Project:
        model = self._session.get(ProjectModel, project.id)
        if model is None:
            model = ProjectModel()
            self._session.add(model)
        apply_project_to_model(project, model)
        self._session.flush()
        return project_to_domain(model)

    def delete(self, project_id: UUID) -> bool:
        model = self._session.get(ProjectModel, project_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True


class SqlAlchemyAreaOfInterestRepository:
    """``AreaOfInterestRepository`` backed by PostGIS via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, aoi: AreaOfInterest) -> AreaOfInterest:
        model = AreaOfInterestModel()
        apply_aoi_to_model(aoi, model)
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return aoi_to_domain(model)

    def get_by_id(self, aoi_id: UUID) -> AreaOfInterest | None:
        model = self._session.get(AreaOfInterestModel, aoi_id)
        return aoi_to_domain(model) if model else None

    def list_by_project(
        self,
        project_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AreaOfInterest]:
        statement = (
            select(AreaOfInterestModel)
            .where(AreaOfInterestModel.project_id == project_id)
            .order_by(AreaOfInterestModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [aoi_to_domain(m) for m in self._session.scalars(statement).all()]

    def save(self, aoi: AreaOfInterest) -> AreaOfInterest:
        model = self._session.get(AreaOfInterestModel, aoi.id)
        if model is None:
            model = AreaOfInterestModel()
            self._session.add(model)
        apply_aoi_to_model(aoi, model)
        self._session.flush()
        self._session.refresh(model)
        return aoi_to_domain(model)

    def delete(self, aoi_id: UUID) -> bool:
        model = self._session.get(AreaOfInterestModel, aoi_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True


class SqlAlchemyScoringProfileRepository:
    """``ScoringProfileRepository`` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, profile: ScoringProfile) -> ScoringProfile:
        model = ScoringProfileModel()
        apply_scoring_profile_to_model(profile, model)
        self._session.add(model)
        self._session.flush()
        return scoring_profile_to_domain(model)

    def get_by_id(self, profile_id: UUID) -> ScoringProfile | None:
        model = self._session.get(ScoringProfileModel, profile_id)
        return scoring_profile_to_domain(model) if model else None

    def list(self, *, limit: int = 50, offset: int = 0) -> list[ScoringProfile]:
        statement = (
            select(ScoringProfileModel)
            .order_by(ScoringProfileModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [scoring_profile_to_domain(m) for m in self._session.scalars(statement).all()]

    def list_by_owner(
        self,
        owner_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ScoringProfile]:
        statement = (
            select(ScoringProfileModel)
            .where(ScoringProfileModel.owner_id == owner_id)
            .order_by(ScoringProfileModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [scoring_profile_to_domain(m) for m in self._session.scalars(statement).all()]

    def save(self, profile: ScoringProfile) -> ScoringProfile:
        model = self._session.get(ScoringProfileModel, profile.id)
        if model is None:
            model = ScoringProfileModel()
            self._session.add(model)
        apply_scoring_profile_to_model(profile, model)
        self._session.flush()
        return scoring_profile_to_domain(model)

    def delete(self, profile_id: UUID) -> bool:
        model = self._session.get(ScoringProfileModel, profile_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True


class SqlAlchemyAnalysisJobRepository:
    """``AnalysisJobRepository`` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: AnalysisJob) -> AnalysisJob:
        model = AnalysisJobModel()
        apply_analysis_job_to_model(job, model)
        self._session.add(model)
        self._session.flush()
        return analysis_job_to_domain(model)

    def get_by_id(self, job_id: UUID) -> AnalysisJob | None:
        model = self._session.get(AnalysisJobModel, job_id)
        return analysis_job_to_domain(model) if model else None

    def list_by_project(
        self,
        project_id: UUID,
        *,
        status: AnalysisJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisJob]:
        statement = select(AnalysisJobModel).where(AnalysisJobModel.project_id == project_id)
        if status is not None:
            statement = statement.where(AnalysisJobModel.status == status.value)
        statement = (
            statement.order_by(AnalysisJobModel.created_at.desc()).limit(limit).offset(offset)
        )
        return [analysis_job_to_domain(m) for m in self._session.scalars(statement).all()]

    def list_by_aoi(
        self,
        aoi_id: UUID,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> list[AnalysisJob]:
        statement = (
            select(AnalysisJobModel)
            .where(AnalysisJobModel.aoi_id == aoi_id)
            .order_by(AnalysisJobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [analysis_job_to_domain(m) for m in self._session.scalars(statement).all()]

    def save(self, job: AnalysisJob) -> AnalysisJob:
        model = self._session.get(AnalysisJobModel, job.id)
        if model is None:
            model = AnalysisJobModel()
            self._session.add(model)
        apply_analysis_job_to_model(job, model)
        self._session.flush()
        return analysis_job_to_domain(model)

    def delete(self, job_id: UUID) -> bool:
        model = self._session.get(AnalysisJobModel, job_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True


class SqlAlchemyAnalysisReportRepository:
    """``AnalysisReportRepository`` backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, report: AnalysisReport) -> AnalysisReport:
        existing = self._session.scalar(
            select(AnalysisReportModel).where(
                AnalysisReportModel.analysis_job_id == report.analysis_job_id
            )
        )
        if existing is not None:
            report.id = existing.id
            report.created_at = existing.created_at
            apply_analysis_report_to_model(report, existing)
            self._session.flush()
            return analysis_report_to_domain(existing)

        model = AnalysisReportModel()
        apply_analysis_report_to_model(report, model)
        self._session.add(model)
        self._session.flush()
        return analysis_report_to_domain(model)

    def get_by_id(self, report_id: UUID) -> AnalysisReport | None:
        model = self._session.get(AnalysisReportModel, report_id)
        return analysis_report_to_domain(model) if model else None

    def get_by_job_id(self, job_id: UUID) -> AnalysisReport | None:
        statement = select(AnalysisReportModel).where(
            AnalysisReportModel.analysis_job_id == job_id
        )
        model = self._session.scalar(statement)
        return analysis_report_to_domain(model) if model else None

    def list_by_aoi(
        self,
        aoi_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisReport]:
        statement = (
            select(AnalysisReportModel)
            .where(AnalysisReportModel.aoi_id == aoi_id)
            .order_by(AnalysisReportModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [analysis_report_to_domain(m) for m in self._session.scalars(statement).all()]

    def delete(self, report_id: UUID) -> bool:
        model = self._session.get(AnalysisReportModel, report_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True
