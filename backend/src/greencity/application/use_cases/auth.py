"""Authentication use cases: register, login, resolve current user."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.entities.user import User
from greencity.domain.exceptions import UnauthorizedError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.ports.security import PasswordHasher
from greencity.domain.ports.tokens import AccessTokenService


@dataclass(frozen=True)
class AuthTokens:
    """Issued credentials for a successful login/register."""

    access_token: str
    token_type: str
    user: User


@dataclass(frozen=True)
class LoginCommand:
    """Email/password login input."""

    email: str
    password: str


class RegisterUserUseCase:
    """Create an account and immediately issue an access token."""

    def __init__(
        self,
        create_user: CreateUserUseCase,
        token_service: AccessTokenService,
    ) -> None:
        self._create_user = create_user
        self._token_service = token_service

    def execute(self, command: CreateUserCommand) -> AuthTokens:
        """Register then return bearer credentials."""

        user = self._create_user.execute(command)
        token = self._token_service.create_access_token(user.id, user.email)
        return AuthTokens(access_token=token, token_type="bearer", user=user)


class LoginUserUseCase:
    """Authenticate by email and password."""

    def __init__(
        self,
        uow: UnitOfWork,
        password_hasher: PasswordHasher,
        token_service: AccessTokenService,
    ) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._token_service = token_service

    def execute(self, command: LoginCommand) -> AuthTokens:
        """Return tokens or raise ``UnauthorizedError``."""

        email = command.email.strip().lower()
        user = self._uow.users.get_by_email(email)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid email or password.")
        if not self._password_hasher.verify(command.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")

        token = self._token_service.create_access_token(user.id, user.email)
        return AuthTokens(access_token=token, token_type="bearer", user=user)


class ResolveCurrentUserUseCase:
    """Load the active user for a validated access token subject."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, user_id: UUID) -> User:
        """Return the user or raise ``UnauthorizedError``."""

        user = self._uow.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Authentication required.")
        return user
