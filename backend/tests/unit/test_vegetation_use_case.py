"""Unit tests for RunVegetationAnalysisUseCase."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import numpy as np
import pytest

from greencity.application.use_cases.vegetation import (
    RunVegetationAnalysisCommand,
    RunVegetationAnalysisUseCase,
)
from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.exceptions import ConflictError, NotFoundError
from greencity.domain.value_objects.vegetation import (
    BandStatistics,
    VegetationCoverage,
    VegetationResult,
)
from tests.fakes import InMemoryUnitOfWork


class _StubPipeline:
    """Always returns a fixed ``VegetationResult``."""

    def __init__(self, *, raises: Exception | None = None) -> None:
        self._raises = raises
        self.called_with: dict[str, Any] = {}

    def run(self, **kwargs: Any) -> VegetationResult:
        self.called_with = kwargs
        if self._raises is not None:
            raise self._raises
        stats = BandStatistics(
            minimum=0.1, maximum=0.8, mean=0.45, std=0.1,
            valid_pixels=100, nodata_pixels=0
        )
        coverage = VegetationCoverage.from_masks(50, 50, 0)
        return VegetationResult(ndvi_stats=stats, coverage=coverage, ndvi_threshold=0.2)


def _make_running_job(uow: InMemoryUnitOfWork) -> AnalysisJob:
    job = AnalysisJob(
        project_id=uuid4(),
        aoi_id=uuid4(),
        scoring_profile_id=uuid4(),
    )
    job.start()  # QUEUED → RUNNING
    uow.analysis_jobs._items[job.id] = job
    return job


class TestRunVegetationAnalysisUseCase:
    def _uc(self, pipeline=None):
        uow = InMemoryUnitOfWork()
        job = _make_running_job(uow)
        pipeline = pipeline or _StubPipeline()
        uc = RunVegetationAnalysisUseCase(uow, pipeline)
        return uc, uow, job

    def test_returns_vegetation_result(self):
        uc, uow, job = self._uc()
        red = np.zeros((5, 5))
        nir = np.zeros((5, 5))
        cmd = RunVegetationAnalysisCommand(job_id=job.id, red_band=red, nir_band=nir)
        result = uc.execute(cmd)
        assert result.coverage.vegetated_fraction == pytest.approx(0.5)

    def test_job_marked_completed(self):
        uc, uow, job = self._uc()
        red = np.zeros((5, 5))
        nir = np.zeros((5, 5))
        cmd = RunVegetationAnalysisCommand(job_id=job.id, red_band=red, nir_band=nir)
        uc.execute(cmd)
        updated = uow.analysis_jobs.get_by_id(job.id)
        assert updated.status == AnalysisJobStatus.COMPLETED

    def test_not_found_raises(self):
        uc, _, _ = self._uc()
        cmd = RunVegetationAnalysisCommand(
            job_id=uuid4(),
            red_band=np.zeros((5, 5)),
            nir_band=np.zeros((5, 5)),
        )
        with pytest.raises(NotFoundError):
            uc.execute(cmd)

    def test_non_running_job_raises(self):
        uow = InMemoryUnitOfWork()
        job = AnalysisJob(project_id=uuid4(), aoi_id=uuid4(), scoring_profile_id=uuid4())
        uow.analysis_jobs._items[job.id] = job
        uc = RunVegetationAnalysisUseCase(uow, _StubPipeline())
        cmd = RunVegetationAnalysisCommand(
            job_id=job.id,
            red_band=np.zeros((5, 5)),
            nir_band=np.zeros((5, 5)),
        )
        with pytest.raises(ConflictError):
            uc.execute(cmd)

    def test_pipeline_failure_marks_job_failed(self):
        uc, uow, job = self._uc(pipeline=_StubPipeline(raises=RuntimeError("boom")))
        cmd = RunVegetationAnalysisCommand(
            job_id=job.id,
            red_band=np.zeros((5, 5)),
            nir_band=np.zeros((5, 5)),
        )
        with pytest.raises(RuntimeError):
            uc.execute(cmd)
        updated = uow.analysis_jobs.get_by_id(job.id)
        assert updated.status == AnalysisJobStatus.FAILED
        assert "boom" in (updated.error_message or "")
