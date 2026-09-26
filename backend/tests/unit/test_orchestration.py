"""Unit tests for LangGraph analysis orchestration."""

from __future__ import annotations

from uuid import uuid4

import pytest

from greencity.application.use_cases.analysis_jobs import (
    CreateAnalysisJobCommand,
    CreateAnalysisJobUseCase,
)
from greencity.application.use_cases.aois import CreateAreaOfInterestCommand, CreateAreaOfInterestUseCase
from greencity.application.use_cases.orchestration import (
    RunAnalysisOrchestrationCommand,
    RunAnalysisOrchestrationUseCase,
)
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileCommand,
    CreateScoringProfileUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.entities.analysis_job import AnalysisJobStatus
from greencity.domain.exceptions import NotFoundError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
)
from greencity.infrastructure.agent import LangGraphAnalysisOrchestrator
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork

SAMPLE = {
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


class _StubOsm:
    def fetch(self, geometry: GeoJsonGeometry) -> OsmContext:
        return OsmContext(
            roads=(),
            parks=(),
            buildings=(),
            total_road_length_m=6_000.0,
            total_park_area_m2=8_000.0,
            total_building_area_m2=80_000.0,
            aoi_area_m2=400_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )



class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.35


def _seed(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="agent@example.com", full_name="A", password="secret123")
    )
    project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="P", description="", owner_id=user.id)
    )
    aoi = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id, name="A", description="", geometry=SAMPLE
        )
    )
    profile = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=user.id,
            name="Balanced",
            description="",
            use_balanced_defaults=True,
            is_default=True,
        )
    )
    job = CreateAnalysisJobUseCase(uow).execute(
        CreateAnalysisJobCommand(
            project_id=project.id,
            aoi_id=aoi.id,
            scoring_profile_id=profile.id,
        )
    )
    return job


def test_orchestration_runs_full_graph() -> None:
    uow = InMemoryUnitOfWork()
    job = _seed(uow)
    orchestrator = LangGraphAnalysisOrchestrator(
        uow, _StubOsm(), _StubParkAccess()
    )
    uc = RunAnalysisOrchestrationUseCase(uow, orchestrator)
    result = uc.execute(
        RunAnalysisOrchestrationCommand(
            job_id=job.id,
            vegetation_coverage=0.2,
            green_area_m2=4_000,
            auto_start=True,
        )
    )

    assert result.job.status == AnalysisJobStatus.COMPLETED
    assert result.job.progress_pct == 100
    assert "validate_inputs" in result.analysis.steps_completed
    assert "compute_indicators" in result.analysis.steps_completed
    assert "compute_gds" in result.analysis.steps_completed
    assert "summarise" in result.analysis.steps_completed
    assert 0 <= result.analysis.score.score <= 100
    assert result.analysis.report is not None
    assert len(result.analysis.report.drivers) == 4
    assert result.analysis.summary
    assert result.analysis.indicators.vegetation_coverage == pytest.approx(0.2)


def test_orchestration_job_not_found() -> None:
    uow = InMemoryUnitOfWork()
    orchestrator = LangGraphAnalysisOrchestrator(
        uow, _StubOsm(), _StubParkAccess()
    )
    uc = RunAnalysisOrchestrationUseCase(uow, orchestrator)
    with pytest.raises(NotFoundError):
        uc.execute(RunAnalysisOrchestrationCommand(job_id=uuid4()))


def test_orchestration_marks_failed_on_error() -> None:
    class _BoomOsm:
        def fetch(self, geometry: GeoJsonGeometry) -> OsmContext:
            raise RuntimeError("overpass down")

    uow = InMemoryUnitOfWork()
    job = _seed(uow)
    orchestrator = LangGraphAnalysisOrchestrator(
        uow, _BoomOsm(), _StubParkAccess()
    )
    uc = RunAnalysisOrchestrationUseCase(uow, orchestrator)
    with pytest.raises(RuntimeError, match="overpass down"):
        uc.execute(RunAnalysisOrchestrationCommand(job_id=job.id, auto_start=True))

    failed = uow.analysis_jobs.get_by_id(job.id)
    assert failed is not None
    assert failed.status == AnalysisJobStatus.FAILED
    assert "overpass down" in (failed.error_message or "")
