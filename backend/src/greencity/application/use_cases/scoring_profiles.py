"""Scoring profile CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.value_objects.indicator_weights import IndicatorWeights


@dataclass(frozen=True)
class CreateScoringProfileCommand:
    """Input for creating a scoring profile."""

    owner_id: UUID
    name: str
    description: str
    weights: Mapping[str, float] | None = None
    is_default: bool = False
    use_balanced_defaults: bool = False


@dataclass(frozen=True)
class UpdateScoringProfileCommand:
    """Input for updating mutable scoring profile fields."""

    name: str | None = None
    description: str | None = None
    weights: Mapping[str, float] | None = None
    is_default: bool | None = None


def _resolve_weights(
    weights: Mapping[str, float] | None,
    *,
    use_balanced_defaults: bool,
) -> IndicatorWeights:
    """Build ``IndicatorWeights`` from explicit values or balanced defaults."""

    if use_balanced_defaults and weights is not None:
        raise ValidationError(
            "Provide either explicit weights or use_balanced_defaults, not both."
        )
    if use_balanced_defaults:
        return IndicatorWeights.balanced_default()
    if weights is None:
        raise ValidationError("Indicator weights are required unless use_balanced_defaults is true.")
    return IndicatorWeights.from_mapping(weights)


def _ensure_single_default(uow: UnitOfWork, owner_id: UUID, keep_id: UUID) -> None:
    """Clear ``is_default`` on other profiles owned by the same user."""

    for profile in uow.scoring_profiles.list_by_owner(owner_id, limit=100, offset=0):
        if profile.id != keep_id and profile.is_default:
            profile.clear_default()
            uow.scoring_profiles.save(profile)


class CreateScoringProfileUseCase:
    """Create a scoring profile for an existing user."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, command: CreateScoringProfileCommand) -> ScoringProfile:
        """Persist a new profile or raise if the owner is missing."""

        owner = self._uow.users.get_by_id(command.owner_id)
        if owner is None:
            raise NotFoundError(f"Owner user '{command.owner_id}' was not found.")
        if not owner.is_active:
            raise ValidationError("Cannot create a scoring profile for an inactive user.")

        weights = _resolve_weights(
            command.weights,
            use_balanced_defaults=command.use_balanced_defaults,
        )
        profile = ScoringProfile(
            owner_id=command.owner_id,
            name=command.name,
            description=command.description,
            weights=weights,
            is_default=command.is_default,
        )
        created = self._uow.scoring_profiles.add(profile)
        if created.is_default:
            _ensure_single_default(self._uow, created.owner_id, created.id)
        self._uow.commit()
        return created


class GetScoringProfileUseCase:
    """Fetch a single scoring profile by id."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, profile_id: UUID) -> ScoringProfile:
        """Return the profile or raise ``NotFoundError``."""

        profile = self._uow.scoring_profiles.get_by_id(profile_id)
        if profile is None:
            raise NotFoundError(f"Scoring profile '{profile_id}' was not found.")
        return profile


class ListScoringProfilesUseCase:
    """List scoring profiles, optionally filtered by owner."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        *,
        owner_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ScoringProfile]:
        """Return a page of scoring profiles."""

        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        if owner_id is not None:
            return self._uow.scoring_profiles.list_by_owner(
                owner_id, limit=limit, offset=offset
            )
        return self._uow.scoring_profiles.list(limit=limit, offset=offset)


class UpdateScoringProfileUseCase:
    """Update mutable scoring profile fields."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        profile_id: UUID,
        command: UpdateScoringProfileCommand,
    ) -> ScoringProfile:
        """Apply updates or raise ``NotFoundError``."""

        profile = self._uow.scoring_profiles.get_by_id(profile_id)
        if profile is None:
            raise NotFoundError(f"Scoring profile '{profile_id}' was not found.")

        if command.name is not None:
            profile.rename(command.name)
        if command.description is not None:
            profile.update_description(command.description)
        if command.weights is not None:
            profile.replace_weights(IndicatorWeights.from_mapping(command.weights))
        if command.is_default is True:
            profile.mark_default()
        elif command.is_default is False:
            profile.clear_default()

        saved = self._uow.scoring_profiles.save(profile)
        if saved.is_default:
            _ensure_single_default(self._uow, saved.owner_id, saved.id)
        self._uow.commit()
        return saved


class DeleteScoringProfileUseCase:
    """Permanently delete a scoring profile."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, profile_id: UUID) -> None:
        """Delete the profile or raise ``NotFoundError``."""

        deleted = self._uow.scoring_profiles.delete(profile_id)
        if not deleted:
            raise NotFoundError(f"Scoring profile '{profile_id}' was not found.")
        self._uow.commit()
