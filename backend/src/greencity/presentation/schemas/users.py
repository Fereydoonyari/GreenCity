"""Pydantic schemas for User HTTP resources."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
    """Body for ``POST /users``."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class UserUpdateRequest(BaseModel):
    """Body for ``PATCH /users/{id}``."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Public user representation (never includes password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
