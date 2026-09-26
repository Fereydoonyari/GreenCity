"""Analysis job CRUD and lifecycle use cases."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.ports.repositories import UnitOfWork


@dataclass(frozen=True)
class CreateAnalysisJobCommand:
    """Input for creating an analysis job in ``queued`` status."""

    project_id: UUID
    aoi_id: UUID
    scoring_profile_id: UUID


@dataclass(frozen=True)
class UpdateAnalysisJobProgressCommand:
    """Input for updating a running job's progress."""

    current_step: str
    progress_pct: int


class CreateAnalysisJobUseCase:
    """Create a queued analysis job after validating references."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, command: CreateAnalysisJobCommand) -> AnalysisJob:
        """Persist a new job or raise if references are invalid."""

        project = self._uow.projects.get_by_id(command.project_id)
        if project is None:
            raise NotFoundError(f"Project '{command.project_id}' was not found.")

        aoi = self._uow.areas_of_interest.get_by_id(command.aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{command.aoi_id}' was not found.")
        if aoi.project_id != command.project_id:
            raise ValidationError(
                "Area of interest does not belong to the specified project."
            )

        profile = self._uow.scoring_profiles.get_by_id(command.scoring_profile_id)
        if profile is None:
            raise NotFoundError(
                f"Scoring profile '{command.scoring_profile_id}' was not found."
            )

        job = AnalysisJob(
            project_id=command.project_id,
            aoi_id=command.aoi_id,
            scoring_profile_id=command.scoring_profile_id,
        )
        created = self._uow.analysis_jobs.add(job)
        self._uow.commit()
        return created


class GetAnalysisJobUseCase:
    """Fetch a single analysis job by id."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: UUID) -> AnalysisJob:
        """Return the job or raise ``NotFoundError``."""

        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        return job


class ListAnalysisJobsUseCase:
    """List analysis jobs for a project."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        project_id: UUID,
        *,
        status: AnalysisJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AnalysisJob]:
        """Return a page of jobs for ``project_id``."""

        project = self._uow.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project '{project_id}' was not found.")

        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        return self._uow.analysis_jobs.list_by_project(
            project_id,
            status=status,
            limit=limit,
            offset=offset,
        )


class StartAnalysisJobUseCase:
    """Start a queued analysis job."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: UUID) -> AnalysisJob:
        """Transition the job to ``running``."""

        job = self._require_job(job_id)
        job.start()
        saved = self._uow.analysis_jobs.save(job)
        self._uow.commit()
        return saved

    def _require_job(self, job_id: UUID) -> AnalysisJob:
        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        return job


class CancelAnalysisJobUseCase:
    """Cancel a queued or running analysis job."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: UUID) -> AnalysisJob:
        """Transition the job to ``cancelled``."""

        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        job.cancel()
        saved = self._uow.analysis_jobs.save(job)
        self._uow.commit()
        return saved


class UpdateAnalysisJobProgressUseCase:
    """Update progress metadata on a running job."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: UUID, command: UpdateAnalysisJobProgressCommand) -> AnalysisJob:
        """Apply progress update or raise on invalid state."""

        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        job.update_progress(
            current_step=command.current_step,
            progress_pct=command.progress_pct,
        )
        saved = self._uow.analysis_jobs.save(job)
        self._uow.commit()
        return saved


class CompleteAnalysisJobUseCase:
    """Mark a running analysis job as completed."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: UUID) -> AnalysisJob:
        """Transition the job to ``completed``."""

        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        job.complete()
        saved = self._uow.analysis_jobs.save(job)
        self._uow.commit()
        return saved


class FailAnalysisJobUseCase:
    """Mark an analysis job as failed with an error message."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: UUID, message: str) -> AnalysisJob:
        """Transition the job to ``failed``."""

        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        job.fail(message)
        saved = self._uow.analysis_jobs.save(job)
        self._uow.commit()
        return saved
