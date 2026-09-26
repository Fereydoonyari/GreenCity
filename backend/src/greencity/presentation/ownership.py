"""Ownership helpers shared by HTTP routes."""

from __future__ import annotations

from uuid import UUID

from greencity.domain.entities.project import Project
from greencity.domain.entities.user import User
from greencity.domain.exceptions import ForbiddenError, NotFoundError
from greencity.domain.ports.repositories import UnitOfWork


def require_owned_project(uow: UnitOfWork, project_id: UUID, user: User) -> Project:
    """Return the project if ``user`` owns it; otherwise raise."""

    project = uow.projects.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project '{project_id}' was not found.")
    if project.owner_id != user.id:
        raise ForbiddenError("You do not own this project.")
    return project
