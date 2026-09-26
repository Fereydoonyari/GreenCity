"""User CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.entities.user import User
from greencity.domain.exceptions import ConflictError, NotFoundError, ValidationError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.ports.security import PasswordHasher


@dataclass(frozen=True)
class CreateUserCommand:
    """Input for creating a user."""

    email: str
    full_name: str
    password: str


@dataclass(frozen=True)
class UpdateUserCommand:
    """Input for updating mutable user fields."""

    full_name: str | None = None
    is_active: bool | None = None


class CreateUserUseCase:
    """Register a new user with a hashed password."""

    def __init__(self, uow: UnitOfWork, password_hasher: PasswordHasher) -> None:
        self._uow = uow
        self._password_hasher = password_hasher

    def execute(self, command: CreateUserCommand) -> User:
        """Create a user or raise ``ConflictError`` if email exists."""

        if len(command.password) < 8:
            raise ValidationError("Password must be at least 8 characters.")

        email = command.email.strip().lower()
        if self._uow.users.get_by_email(email) is not None:
            raise ConflictError(f"User with email '{email}' already exists.")

        user = User(
            email=email,
            full_name=command.full_name,
            password_hash=self._password_hasher.hash(command.password),
        )
        created = self._uow.users.add(user)
        self._uow.commit()
        return created


class GetUserUseCase:
    """Fetch a single user by id."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, user_id: UUID) -> User:
        """Return the user or raise ``NotFoundError``."""

        user = self._uow.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User '{user_id}' was not found.")
        return user


class ListUsersUseCase:
    """List users with simple offset pagination."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        """Return a page of users."""

        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        return self._uow.users.list(limit=limit, offset=offset)


class UpdateUserUseCase:
    """Update mutable user profile fields."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, user_id: UUID, command: UpdateUserCommand) -> User:
        """Apply updates or raise ``NotFoundError``."""

        user = self._uow.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User '{user_id}' was not found.")

        if command.full_name is not None:
            user.rename(command.full_name)
        if command.is_active is True:
            user.activate()
        elif command.is_active is False:
            user.deactivate()

        saved = self._uow.users.save(user)
        self._uow.commit()
        return saved


class DeleteUserUseCase:
    """Permanently delete a user account."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, user_id: UUID) -> None:
        """Delete the user or raise ``NotFoundError``."""

        deleted = self._uow.users.delete(user_id)
        if not deleted:
            raise NotFoundError(f"User '{user_id}' was not found.")
        self._uow.commit()
