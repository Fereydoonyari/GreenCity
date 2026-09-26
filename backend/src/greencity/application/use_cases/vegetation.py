"""Use case: run the full vegetation analysis pipeline for an analysis job.

This use case:
1. Loads the job, verifies it is in RUNNING state.
2. Delegates to ``VegetationPipelinePort`` (injected) with synthetic or
   pre-loaded band arrays.
3. Reports progress at each stage by calling ``update_progress``.
4. Marks the job ``completed`` (or ``failed`` on exception).
5. Returns the ``VegetationResult``.

Band arrays are injected by the caller (in-memory fixtures in tests,
HLS rasters in production).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.exceptions import ConflictError, NotFoundError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.ports.vegetation import VegetationPipelinePort
from greencity.domain.value_objects.vegetation import VegetationResult

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunVegetationAnalysisCommand:
    """Input for the vegetation analysis run use case.

    Args:
        job_id: UUID of an existing ``RUNNING`` analysis job.
        red_band: 2-D array-like for the red (Band 4 / B04) channel.
        nir_band: 2-D array-like for the NIR (Band 5 / B8A) channel.
        nodata_mask: Optional boolean mask where ``True`` is invalid.
        ndvi_threshold: Classification threshold (default 0.2).
        pixel_size_m: Ground sampling distance in metres (optional).
    """

    job_id: UUID
    red_band: Any
    nir_band: Any
    nodata_mask: Any | None = None
    ndvi_threshold: float = 0.2
    pixel_size_m: float | None = None


class RunVegetationAnalysisUseCase:
    """Orchestrate the vegetation analysis pipeline for a single job.

    Implements a progress-reporting wrapper around the infrastructure
    ``VegetationPipelinePort``:

    - 10 % — validation
    - 30 % — NDVI computation (reported by the pipeline stage)
    - 70 % — polygon extraction
    - 100 % — completed

    The job must already be in ``RUNNING`` status before this use case is
    called.  Use ``StartAnalysisJobUseCase`` first.
    """

    def __init__(self, uow: UnitOfWork, pipeline: VegetationPipelinePort) -> None:
        self._uow = uow
        self._pipeline = pipeline

    def execute(self, command: RunVegetationAnalysisCommand) -> VegetationResult:
        """Run the pipeline and update the job's status.

        Args:
            command: Validated input containing job ID and band arrays.

        Returns:
            ``VegetationResult`` with NDVI stats, coverage, and polygons.

        Raises:
            NotFoundError: When the job does not exist.
            ConflictError: When the job is not in ``RUNNING`` state.
        """
        job = self._uow.analysis_jobs.get_by_id(command.job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{command.job_id}' was not found.")
        if job.status != AnalysisJobStatus.RUNNING:
            raise ConflictError(
                f"Job must be RUNNING to execute the pipeline "
                f"(current status: '{job.status.value}')."
            )

        self._progress(job, step="preprocessing", pct=10)

        try:
            result = self._pipeline.run(
                red_band=command.red_band,
                nir_band=command.nir_band,
                nodata_mask=command.nodata_mask,
                ndvi_threshold=command.ndvi_threshold,
                pixel_size_m=command.pixel_size_m,
            )
        except Exception as exc:  # noqa: BLE001
            _log.exception("Vegetation pipeline failed for job %s", command.job_id)
            job.fail(str(exc) or "Pipeline error.")
            self._uow.analysis_jobs.save(job)
            self._uow.commit()
            raise

        self._progress(job, step="completed", pct=100)
        job.complete()
        self._uow.analysis_jobs.save(job)
        self._uow.commit()

        _log.info(
            "Job %s completed – vegetated fraction %.2f%%",
            command.job_id,
            result.coverage.vegetated_fraction * 100,
        )
        return result

    def _progress(self, job: AnalysisJob, *, step: str, pct: int) -> None:
        job.update_progress(current_step=step, progress_pct=pct)
        self._uow.analysis_jobs.save(job)
        self._uow.commit()
