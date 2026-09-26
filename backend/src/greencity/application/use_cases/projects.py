"""Project CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.entities.project import Project, ProjectStatus
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.ports.repositories import UnitOfWork


@dataclass(frozen=True)
class CreateProjectCommand:
    """Input for creating a project."""

    name: str
    description: str
    owner_id: UUID
    status: ProjectStatus = ProjectStatus.DRAFT


@dataclass(frozen=True)
class UpdateProjectCommand:
    """Input for updating mutable project fields."""

    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class CreateProjectUseCase:
    """Create a planning project owned by an existing user."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, command: CreateProjectCommand) -> Project:
        """Create a project or raise if the owner does not exist."""

        owner = self._uow.users.get_by_id(command.owner_id)
        if owner is None:
            raise NotFoundError(f"Owner user '{command.owner_id}' was not found.")
        if not owner.is_active:
            raise ValidationError("Cannot create a project for an inactive user.")

        project = Project(
            name=command.name,
            description=command.description,
            owner_id=command.owner_id,
            status=command.status,
        )
        created = self._uow.projects.add(project)
        self._uow.commit()
        return created


class GetProjectUseCase:
    """Fetch a single project by id."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, project_id: UUID) -> Project:
        """Return the project or raise ``NotFoundError``."""

        project = self._uow.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project '{project_id}' was not found.")
        return project


class ListProjectsUseCase:
    """List projects with optional owner filter."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        *,
        owner_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        """Return a page of projects."""

        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        return self._uow.projects.list(owner_id=owner_id, limit=limit, offset=offset)


class UpdateProjectUseCase:
    """Update mutable project fields."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, project_id: UUID, command: UpdateProjectCommand) -> Project:
        """Apply updates or raise ``NotFoundError``."""

        project = self._uow.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project '{project_id}' was not found.")

        if command.name is not None:
            project.rename(command.name)
        if command.description is not None:
            project.update_description(command.description)
        if command.status is not None:
            project.change_status(command.status)

        saved = self._uow.projects.save(project)
        self._uow.commit()
        return saved


class DeleteProjectUseCase:
    """Permanently delete a project."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, project_id: UUID) -> None:
        """Delete the project or raise ``NotFoundError``."""

        deleted = self._uow.projects.delete(project_id)
        if not deleted:
            raise NotFoundError(f"Project '{project_id}' was not found.")
        self._uow.commit()
