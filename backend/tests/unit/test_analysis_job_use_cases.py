"""Unit tests for analysis job use cases."""

import pytest

from greencity.application.use_cases.analysis_jobs import (
    CancelAnalysisJobUseCase,
    CompleteAnalysisJobUseCase,
    CreateAnalysisJobCommand,
    CreateAnalysisJobUseCase,
    FailAnalysisJobUseCase,
    ListAnalysisJobsUseCase,
    StartAnalysisJobUseCase,
    UpdateAnalysisJobProgressCommand,
    UpdateAnalysisJobProgressUseCase,
)
from greencity.application.use_cases.aois import CreateAreaOfInterestCommand, CreateAreaOfInterestUseCase
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileCommand,
    CreateScoringProfileUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.entities.analysis_job import AnalysisJobStatus
from greencity.domain.exceptions import ConflictError, NotFoundError, ValidationError
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.35, 48.85],
            [2.36, 48.85],
            [2.36, 48.86],
            [2.35, 48.86],
            [2.35, 48.85],
        ]
    ],
}


def _seed(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="jobs@city.gov", full_name="Jobs", password="secret123")
    )
    project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="Pilot", description="", owner_id=user.id)
    )
    aoi = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="AOI",
            description="",
            geometry=SAMPLE_POLYGON,
        )
    )
    profile = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=user.id,
            name="Balanced",
            description="",
            use_balanced_defaults=True,
        )
    )
    return project, aoi, profile


def test_create_and_lifecycle() -> None:
    uow = InMemoryUnitOfWork()
    project, aoi, profile = _seed(uow)

    job = CreateAnalysisJobUseCase(uow).execute(
        CreateAnalysisJobCommand(
            project_id=project.id,
            aoi_id=aoi.id,
            scoring_profile_id=profile.id,
        )
    )
    assert job.status == AnalysisJobStatus.QUEUED

    started = StartAnalysisJobUseCase(uow).execute(job.id)
    assert started.status == AnalysisJobStatus.RUNNING

    progressed = UpdateAnalysisJobProgressUseCase(uow).execute(
        job.id,
        UpdateAnalysisJobProgressCommand(current_step="ndvi", progress_pct=40),
    )
    assert progressed.progress_pct == 40

    completed = CompleteAnalysisJobUseCase(uow).execute(job.id)
    assert completed.status == AnalysisJobStatus.COMPLETED

    listed = ListAnalysisJobsUseCase(uow).execute(project.id)
    assert len(listed) == 1


def test_aoi_must_belong_to_project() -> None:
    uow = InMemoryUnitOfWork()
    project, aoi, profile = _seed(uow)
    other_project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="Other", description="", owner_id=project.owner_id)
    )

    with pytest.raises(ValidationError):
        CreateAnalysisJobUseCase(uow).execute(
            CreateAnalysisJobCommand(
                project_id=other_project.id,
                aoi_id=aoi.id,
                scoring_profile_id=profile.id,
            )
        )


def test_cancel_and_invalid_complete() -> None:
    uow = InMemoryUnitOfWork()
    project, aoi, profile = _seed(uow)
    job = CreateAnalysisJobUseCase(uow).execute(
        CreateAnalysisJobCommand(
            project_id=project.id,
            aoi_id=aoi.id,
            scoring_profile_id=profile.id,
        )
    )
    CancelAnalysisJobUseCase(uow).execute(job.id)
    with pytest.raises(ConflictError):
        StartAnalysisJobUseCase(uow).execute(job.id)


def test_fail_job() -> None:
    uow = InMemoryUnitOfWork()
    project, aoi, profile = _seed(uow)
    job = CreateAnalysisJobUseCase(uow).execute(
        CreateAnalysisJobCommand(
            project_id=project.id,
            aoi_id=aoi.id,
            scoring_profile_id=profile.id,
        )
    )
    StartAnalysisJobUseCase(uow).execute(job.id)
    failed = FailAnalysisJobUseCase(uow).execute(job.id, "timeout")
    assert failed.status == AnalysisJobStatus.FAILED
    assert failed.error_message == "timeout"


def test_create_missing_project() -> None:
    from uuid import uuid4

    uow = InMemoryUnitOfWork()
    with pytest.raises(NotFoundError):
        CreateAnalysisJobUseCase(uow).execute(
            CreateAnalysisJobCommand(
                project_id=uuid4(),
                aoi_id=uuid4(),
                scoring_profile_id=uuid4(),
            )
        )
