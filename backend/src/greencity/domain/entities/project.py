"""Project aggregate – a green-infrastructure planning workspace."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from greencity.domain.entities.base import Entity
from greencity.domain.exceptions import ValidationError


class ProjectStatus(StrEnum):
    """Lifecycle status for a planning project."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(kw_only=True)
class Project(Entity):
    """Planning project owned by a single user.

    Later features attach AOIs, analysis jobs, and reports to this aggregate.
    """

    name: str
    description: str
    owner_id: UUID
    status: ProjectStatus = ProjectStatus.DRAFT

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValidationError("Project name must not be empty.")
        if not isinstance(self.status, ProjectStatus):
            self.status = ProjectStatus(self.status)

    def rename(self, name: str) -> None:
        """Change the project name."""

        cleaned = name.strip()
        if not cleaned:
            raise ValidationError("Project name must not be empty.")
        self.name = cleaned
        self.touch()

    def update_description(self, description: str) -> None:
        """Replace the project description."""

        self.description = description.strip()
        self.touch()

    def change_status(self, status: ProjectStatus) -> None:
        """Transition project lifecycle status."""

        if not isinstance(status, ProjectStatus):
            status = ProjectStatus(status)
        self.status = status
        self.touch()
