"""Use case: run LangGraph analysis orchestration for a job."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.exceptions import ConflictError, NotFoundError
from greencity.domain.ports.orchestration import AnalysisOrchestratorPort
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.value_objects.orchestration import AnalysisOrchestrationResult


@dataclass(frozen=True)
class RunAnalysisOrchestrationCommand:
    """Input for orchestrating a full analysis job."""

    job_id: UUID
    vegetation_coverage: float | None = None
    green_area_m2: float | None = None
    park_walk_distance_m: float = 300.0
    auto_start: bool = True


@dataclass(frozen=True)
class RunAnalysisOrchestrationResult:
    """Job snapshot after orchestration plus structured analysis output."""

    job: AnalysisJob
    analysis: AnalysisOrchestrationResult


class RunAnalysisOrchestrationUseCase:
    """Start (optional) and orchestrate an analysis job via the agent port.

    The orchestrator owns progress updates and completion/failure. This use
    case only ensures the job exists and is ``RUNNING`` before delegating.
    """

    def __init__(self, uow: UnitOfWork, orchestrator: AnalysisOrchestratorPort) -> None:
        self._uow = uow
        self._orchestrator = orchestrator

    def execute(self, command: RunAnalysisOrchestrationCommand) -> RunAnalysisOrchestrationResult:
        """Run the analysis graph for ``command.job_id``."""

        job = self._uow.analysis_jobs.get_by_id(command.job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{command.job_id}' was not found.")

        if job.status == AnalysisJobStatus.QUEUED and command.auto_start:
            job.start()
            self._uow.analysis_jobs.save(job)
            self._uow.commit()
        elif job.status != AnalysisJobStatus.RUNNING:
            raise ConflictError(
                f"Cannot orchestrate job in status '{job.status.value}' "
                "(expected queued or running)."
            )

        analysis = self._orchestrator.run(
            command.job_id,
            vegetation_coverage=command.vegetation_coverage,
            green_area_m2=command.green_area_m2,
            park_walk_distance_m=command.park_walk_distance_m,
        )

        # Re-load job after orchestrator commits completion.
        updated = self._uow.analysis_jobs.get_by_id(command.job_id)
        if updated is None:
            raise NotFoundError(f"Analysis job '{command.job_id}' was not found.")
        return RunAnalysisOrchestrationResult(job=updated, analysis=analysis)
