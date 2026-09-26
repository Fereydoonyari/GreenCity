"""Pydantic schemas for Project HTTP resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from greencity.domain.entities.project import ProjectStatus


class ProjectCreateRequest(BaseModel):
    """Body for ``POST /projects`` (owner is always the authenticated user)."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: ProjectStatus = ProjectStatus.DRAFT


class ProjectUpdateRequest(BaseModel):
    """Body for ``PATCH /projects/{id}``."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    """Public project representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    owner_id: UUID
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
