"""Unit tests for AOI use cases."""

import pytest

from greencity.application.use_cases.aois import (
    CreateAreaOfInterestCommand,
    CreateAreaOfInterestUseCase,
    DeleteAreaOfInterestUseCase,
    GetAreaOfInterestUseCase,
    ListAreasOfInterestUseCase,
    UpdateAreaOfInterestCommand,
    UpdateAreaOfInterestUseCase,
)
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.exceptions import NotFoundError, ValidationError
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


def _seed_project(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="aoi@city.gov", full_name="AOI Owner", password="secret123")
    )
    return CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="Paris Pilot", description="", owner_id=user.id)
    )


def test_create_aoi_for_project() -> None:
    uow = InMemoryUnitOfWork()
    project = _seed_project(uow)

    aoi = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="Arrondissement sample",
            description="Test",
            geometry=SAMPLE_POLYGON,
        )
    )

    assert aoi.project_id == project.id
    assert aoi.geometry.geometry_type == "Polygon"
    assert uow.committed is True


def test_create_aoi_unwraps_feature() -> None:
    uow = InMemoryUnitOfWork()
    project = _seed_project(uow)

    aoi = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="Feature AOI",
            description="",
            geometry={"type": "Feature", "properties": {}, "geometry": SAMPLE_POLYGON},
        )
    )
    assert aoi.geometry.data["type"] == "Polygon"


def test_list_update_delete_aoi() -> None:
    uow = InMemoryUnitOfWork()
    project = _seed_project(uow)
    created = CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="A",
            description="",
            geometry=SAMPLE_POLYGON,
        )
    )

    listed = ListAreasOfInterestUseCase(uow).execute(project.id)
    assert len(listed) == 1

    updated = UpdateAreaOfInterestUseCase(uow).execute(
        created.id,
        UpdateAreaOfInterestCommand(name="B"),
    )
    assert updated.name == "B"

    DeleteAreaOfInterestUseCase(uow).execute(created.id)
    with pytest.raises(NotFoundError):
        GetAreaOfInterestUseCase(uow).execute(created.id)


def test_create_aoi_requires_project() -> None:
    from uuid import uuid4

    uow = InMemoryUnitOfWork()
    with pytest.raises(NotFoundError):
        CreateAreaOfInterestUseCase(uow).execute(
            CreateAreaOfInterestCommand(
                project_id=uuid4(),
                name="X",
                description="",
                geometry=SAMPLE_POLYGON,
            )
        )


def test_invalid_geometry_rejected() -> None:
    uow = InMemoryUnitOfWork()
    project = _seed_project(uow)
    with pytest.raises(ValidationError):
        CreateAreaOfInterestUseCase(uow).execute(
            CreateAreaOfInterestCommand(
                project_id=project.id,
                name="Bad",
                description="",
                geometry={"type": "Point", "coordinates": [0, 0]},
            )
        )
