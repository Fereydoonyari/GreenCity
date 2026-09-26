"""Unit tests for user use cases."""

import pytest

from greencity.application.use_cases.users import (
    CreateUserCommand,
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    UpdateUserCommand,
    UpdateUserUseCase,
)
from greencity.domain.exceptions import ConflictError, NotFoundError, ValidationError
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork


def test_create_user_hashes_password_and_commits() -> None:
    uow = InMemoryUnitOfWork()
    use_case = CreateUserUseCase(uow, FakePasswordHasher())

    user = use_case.execute(
        CreateUserCommand(email=" Planner@City.gov ", full_name="Ada", password="secret123")
    )

    assert user.email == "planner@city.gov"
    assert user.password_hash == "hashed:secret123"
    assert uow.committed is True


def test_create_user_rejects_duplicate_email() -> None:
    uow = InMemoryUnitOfWork()
    use_case = CreateUserUseCase(uow, FakePasswordHasher())
    use_case.execute(CreateUserCommand(email="a@b.com", full_name="A", password="secret123"))

    with pytest.raises(ConflictError):
        use_case.execute(CreateUserCommand(email="a@b.com", full_name="B", password="secret123"))


def test_create_user_rejects_short_password() -> None:
    uow = InMemoryUnitOfWork()
    use_case = CreateUserUseCase(uow, FakePasswordHasher())

    with pytest.raises(ValidationError):
        use_case.execute(CreateUserCommand(email="a@b.com", full_name="A", password="short"))


def test_get_user_not_found() -> None:
    from uuid import uuid4

    use_case = GetUserUseCase(InMemoryUnitOfWork())
    with pytest.raises(NotFoundError):
        use_case.execute(uuid4())


def test_update_and_delete_user() -> None:
    uow = InMemoryUnitOfWork()
    created = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="a@b.com", full_name="A", password="secret123")
    )

    updated = UpdateUserUseCase(uow).execute(
        created.id,
        UpdateUserCommand(full_name="Ada Lovelace", is_active=False),
    )
    assert updated.full_name == "Ada Lovelace"
    assert updated.is_active is False

    DeleteUserUseCase(uow).execute(created.id)
    with pytest.raises(NotFoundError):
        GetUserUseCase(uow).execute(created.id)
