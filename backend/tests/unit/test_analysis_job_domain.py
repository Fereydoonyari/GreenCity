"""Unit tests for AnalysisJob domain transitions."""

import pytest

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.exceptions import ConflictError, ValidationError
from uuid import uuid4


def _job() -> AnalysisJob:
    return AnalysisJob(
        project_id=uuid4(),
        aoi_id=uuid4(),
        scoring_profile_id=uuid4(),
    )


def test_start_complete_happy_path() -> None:
    job = _job()
    assert job.status == AnalysisJobStatus.QUEUED
    job.start()
    assert job.status == AnalysisJobStatus.RUNNING
    assert job.started_at is not None
    job.update_progress(current_step="computing_indicators", progress_pct=60)
    job.complete()
    assert job.status == AnalysisJobStatus.COMPLETED
    assert job.progress_pct == 100
    assert job.completed_at is not None


def test_cannot_start_twice() -> None:
    job = _job()
    job.start()
    with pytest.raises(ConflictError):
        job.start()


def test_cancel_from_queued() -> None:
    job = _job()
    job.cancel()
    assert job.status == AnalysisJobStatus.CANCELLED
    with pytest.raises(ConflictError):
        job.start()


def test_fail_requires_message() -> None:
    job = _job()
    job.start()
    with pytest.raises(ValidationError):
        job.fail("  ")
    job.fail("imagery unavailable")
    assert job.status == AnalysisJobStatus.FAILED
    assert job.error_message == "imagery unavailable"
