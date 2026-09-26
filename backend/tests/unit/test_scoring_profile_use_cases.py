"""Unit tests for scoring profile use cases."""

import pytest

from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileCommand,
    CreateScoringProfileUseCase,
    DeleteScoringProfileUseCase,
    GetScoringProfileUseCase,
    ListScoringProfilesUseCase,
    UpdateScoringProfileCommand,
    UpdateScoringProfileUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.value_objects.indicator_weights import IndicatorWeights
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork


def _seed_owner(uow: InMemoryUnitOfWork):
    return CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="scorer@city.gov", full_name="Scorer", password="secret123")
    )


def test_create_balanced_default_profile() -> None:
    uow = InMemoryUnitOfWork()
    owner = _seed_owner(uow)

    profile = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=owner.id,
            name="Balanced",
            description="",
            use_balanced_defaults=True,
            is_default=True,
        )
    )

    assert profile.is_default is True
    assert abs(sum(profile.weights.as_dict().values()) - 1.0) < 1e-9
    assert uow.committed is True


def test_create_with_custom_weights() -> None:
    uow = InMemoryUnitOfWork()
    owner = _seed_owner(uow)
    weights = IndicatorWeights.balanced_default().as_dict()

    profile = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=owner.id,
            name="Custom",
            description="tune vegetation",
            weights=weights,
        )
    )
    assert profile.name == "Custom"


def test_ensures_single_default_per_owner() -> None:
    uow = InMemoryUnitOfWork()
    owner = _seed_owner(uow)
    first = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=owner.id,
            name="A",
            description="",
            use_balanced_defaults=True,
            is_default=True,
        )
    )
    second = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=owner.id,
            name="B",
            description="",
            use_balanced_defaults=True,
            is_default=True,
        )
    )

    refreshed_first = GetScoringProfileUseCase(uow).execute(first.id)
    assert refreshed_first.is_default is False
    assert second.is_default is True


def test_update_list_delete() -> None:
    uow = InMemoryUnitOfWork()
    owner = _seed_owner(uow)
    created = CreateScoringProfileUseCase(uow).execute(
        CreateScoringProfileCommand(
            owner_id=owner.id,
            name="A",
            description="",
            use_balanced_defaults=True,
        )
    )

    updated = UpdateScoringProfileUseCase(uow).execute(
        created.id,
        UpdateScoringProfileCommand(name="Access-first", is_default=True),
    )
    assert updated.name == "Access-first"
    assert updated.is_default is True

    listed = ListScoringProfilesUseCase(uow).execute(owner_id=owner.id)
    assert len(listed) == 1

    DeleteScoringProfileUseCase(uow).execute(created.id)
    with pytest.raises(NotFoundError):
        GetScoringProfileUseCase(uow).execute(created.id)


def test_create_requires_owner() -> None:
    from uuid import uuid4

    uow = InMemoryUnitOfWork()
    with pytest.raises(NotFoundError):
        CreateScoringProfileUseCase(uow).execute(
            CreateScoringProfileCommand(
                owner_id=uuid4(),
                name="X",
                description="",
                use_balanced_defaults=True,
            )
        )


def test_rejects_weights_and_defaults_together() -> None:
    uow = InMemoryUnitOfWork()
    owner = _seed_owner(uow)
    with pytest.raises(ValidationError):
        CreateScoringProfileUseCase(uow).execute(
            CreateScoringProfileCommand(
                owner_id=owner.id,
                name="X",
                description="",
                use_balanced_defaults=True,
                weights=IndicatorWeights.balanced_default().as_dict(),
            )
        )
