"""Unit tests for project use cases."""

import pytest

from greencity.application.use_cases.projects import (
    CreateProjectCommand,
    CreateProjectUseCase,
    DeleteProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
    UpdateProjectCommand,
    UpdateProjectUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.entities.project import ProjectStatus
from greencity.domain.exceptions import NotFoundError
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork


def _seed_owner(uow: InMemoryUnitOfWork):
    return CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="owner@city.gov", full_name="Owner", password="secret123")
    )


def test_create_project_requires_existing_owner() -> None:
    from uuid import uuid4

    uow = InMemoryUnitOfWork()
    with pytest.raises(NotFoundError):
        CreateProjectUseCase(uow).execute(
            CreateProjectCommand(name="Park Plan", description="", owner_id=uuid4())
        )


def test_project_crud_flow() -> None:
    uow = InMemoryUnitOfWork()
    owner = _seed_owner(uow)

    created = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(
            name="Green Corridor",
            description="Pilot",
            owner_id=owner.id,
            status=ProjectStatus.ACTIVE,
        )
    )
    assert created.status == ProjectStatus.ACTIVE

    listed = ListProjectsUseCase(uow).execute(owner_id=owner.id)
    assert len(listed) == 1

    updated = UpdateProjectUseCase(uow).execute(
        created.id,
        UpdateProjectCommand(name="Green Corridor v2", status=ProjectStatus.ARCHIVED),
    )
    assert updated.name == "Green Corridor v2"
    assert updated.status == ProjectStatus.ARCHIVED

    DeleteProjectUseCase(uow).execute(created.id)
    with pytest.raises(NotFoundError):
        GetProjectUseCase(uow).execute(created.id)
