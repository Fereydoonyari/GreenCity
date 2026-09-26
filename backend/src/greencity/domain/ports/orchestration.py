"""Port for analysis-job agent orchestration."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from greencity.domain.value_objects.orchestration import AnalysisOrchestrationResult


class AnalysisOrchestratorPort(Protocol):
    """Orchestrate a full analysis pipeline for a running job.

    Implementations live in infrastructure (LangGraph). They must call
    application use cases / domain services for science – never recompute
    indicators or scores inside an LLM prompt.
    """

    def run(
        self,
        job_id: UUID,
        *,
        vegetation_coverage: float | None = None,
        green_area_m2: float | None = None,
        park_walk_distance_m: float = 300.0,
    ) -> AnalysisOrchestrationResult:
        """Execute the analysis graph and return structured results.

        The job must already be in ``RUNNING`` status. On failure the
        implementation should mark the job ``failed`` before re-raising.
        """
        ...
