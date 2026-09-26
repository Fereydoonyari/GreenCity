"""Unit tests for city / neighborhood AOI hierarchy rules."""

from uuid import uuid4

import pytest

from greencity.application.use_cases.aois import (
    CreateAreaOfInterestCommand,
    CreateAreaOfInterestUseCase,
)
from greencity.domain.entities.aoi import AoiKind
from greencity.domain.entities.project import Project
from greencity.domain.entities.user import User
from greencity.domain.exceptions import ConflictError, ValidationError
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork

SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.0, 48.0],
            [2.1, 48.0],
            [2.1, 48.1],
            [2.0, 48.1],
            [2.0, 48.0],
        ]
    ],
}


def _seed_project(uow: InMemoryUnitOfWork) -> Project:
    hasher = FakePasswordHasher()
    user = User(
        email="a@b.co",
        full_name="A",
        password_hash=hasher.hash("secret123"),
    )
    uow.users.add(user)
    project = Project(
        name="Study",
        description="",
        owner_id=user.id,
    )
    uow.projects.add(project)
    return project


def test_city_then_neighborhood_parent() -> None:
    uow = InMemoryUnitOfWork()
    project = _seed_project(uow)
    use_case = CreateAreaOfInterestUseCase(uow)

    city = use_case.execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="Metro",
            description="",
            geometry=SQUARE,
            kind=AoiKind.CITY,
        )
    )
    assert city.kind == AoiKind.CITY

    hood = use_case.execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="Downtown",
            description="",
            geometry=SQUARE,
            kind=AoiKind.NEIGHBORHOOD,
            parent_aoi_id=city.id,
        )
    )
    assert hood.parent_aoi_id == city.id


def test_only_one_city_per_project() -> None:
    uow = InMemoryUnitOfWork()
    project = _seed_project(uow)
    use_case = CreateAreaOfInterestUseCase(uow)
    use_case.execute(
        CreateAreaOfInterestCommand(
            project_id=project.id,
            name="Metro",
            description="",
            geometry=SQUARE,
            kind=AoiKind.CITY,
        )
    )
    with pytest.raises(ConflictError):
        use_case.execute(
            CreateAreaOfInterestCommand(
                project_id=project.id,
                name="Metro 2",
                description="",
                geometry=SQUARE,
                kind=AoiKind.CITY,
            )
        )


def test_city_cannot_have_parent() -> None:
    uow = InMemoryUnitOfWork()
    project = _seed_project(uow)
    use_case = CreateAreaOfInterestUseCase(uow)
    with pytest.raises(ValidationError):
        use_case.execute(
            CreateAreaOfInterestCommand(
                project_id=project.id,
                name="Metro",
                description="",
                geometry=SQUARE,
                kind=AoiKind.CITY,
                parent_aoi_id=uuid4(),
            )
        )
