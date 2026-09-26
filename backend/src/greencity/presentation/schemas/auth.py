"""Auth HTTP schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from greencity.presentation.schemas.users import UserResponse


class RegisterRequest(BaseModel):
    """Body for ``POST /auth/register``."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Body for ``POST /auth/login``."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Bearer token plus the authenticated user profile."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MeResponse(BaseModel):
    """Current authenticated user."""

    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
