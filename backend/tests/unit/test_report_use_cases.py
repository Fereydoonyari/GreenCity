"""Unit tests for explainable report use cases."""

from __future__ import annotations

from greencity.application.use_cases.analysis_jobs import (
    CreateAnalysisJobCommand,
    CreateAnalysisJobUseCase,
)
from greencity.application.use_cases.aois import CreateAreaOfInterestCommand, CreateAreaOfInterestUseCase
from greencity.application.use_cases.indicators import ComputeIndicatorsUseCase
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.reports import (
    GenerateReportCommand,
    GenerateReportUseCase,
    GetReportByJobUseCase,
    GetReportUseCase,
)
from greencity.application.use_cases.scoring import ScoreAoiUseCase
from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileCommand,
    CreateScoringProfileUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.exceptions import NotFoundError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
)
from greencity.infrastructure.reporting import TemplateReportExplainer
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork
import pytest

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
            total_road_length_m=4_000.0,
            total_park_area_m2=10_000.0,
            total_building_area_m2=50_000.0,
            aoi_area_m2=350_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )



class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.4


def _seed(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="report@example.com", full_name="R", password="secret123")
    )
    project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="P", description="", owner_id=user.id)
    )
    aoi = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id, name="Riverside", description="", geometry=SAMPLE
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


def test_generate_and_get_report() -> None:
    uow = InMemoryUnitOfWork()
    job = _seed(uow)
    score_aoi = ScoreAoiUseCase(
        uow,
        ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess()),
    )
    generate = GenerateReportUseCase(uow, TemplateReportExplainer(), score_aoi)

    report = generate.execute(
        GenerateReportCommand(
            analysis_job_id=job.id,
            vegetation_coverage=0.22,
            green_area_m2=5_000,
        )
    )

    assert "Riverside" in report.headline
    assert len(report.drivers) == 4
    assert report.source == "template"

    fetched = GetReportUseCase(uow).execute(report.id)
    assert fetched.id == report.id
    by_job = GetReportByJobUseCase(uow).execute(job.id)
    assert by_job.id == report.id


def test_get_report_by_job_missing() -> None:
    uow = InMemoryUnitOfWork()
    job = _seed(uow)
    with pytest.raises(NotFoundError):
        GetReportByJobUseCase(uow).execute(job.id)
