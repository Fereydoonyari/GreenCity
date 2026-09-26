"""Scoring profile aggregate – configurable Green Deficiency weights."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.entities.base import Entity
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.indicator_weights import IndicatorWeights


@dataclass(kw_only=True)
class ScoringProfile(Entity):
    """Named set of indicator weights used when ranking neighborhoods.

    Profiles are owned by a user. Analysis jobs (later feature) will reference
    a profile id so scoring remains explainable and reproducible.
    """

    owner_id: UUID
    name: str
    description: str
    weights: IndicatorWeights
    is_default: bool = False

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValidationError("Scoring profile name must not be empty.")
        if not isinstance(self.weights, IndicatorWeights):
            raise ValidationError("Scoring profile weights must be IndicatorWeights.")

    def rename(self, name: str) -> None:
        """Update the profile display name."""

        cleaned = name.strip()
        if not cleaned:
            raise ValidationError("Scoring profile name must not be empty.")
        self.name = cleaned
        self.touch()

    def update_description(self, description: str) -> None:
        """Replace the profile description."""

        self.description = description.strip()
        self.touch()

    def replace_weights(self, weights: IndicatorWeights) -> None:
        """Replace all indicator weights."""

        if not isinstance(weights, IndicatorWeights):
            raise ValidationError("Scoring profile weights must be IndicatorWeights.")
        self.weights = weights
        self.touch()

    def mark_default(self) -> None:
        """Mark this profile as the owner's default."""

        self.is_default = True
        self.touch()

    def clear_default(self) -> None:
        """Clear the default flag."""

        self.is_default = False
        self.touch()

    @classmethod
    def create_balanced_default(cls, *, owner_id: UUID, name: str = "Balanced default") -> ScoringProfile:
        """Factory for a ready-to-use balanced scoring profile."""

        return cls(
            owner_id=owner_id,
            name=name,
            description="Equal-priority blend of vegetation, access, and demographic pressure.",
            weights=IndicatorWeights.balanced_default(),
            is_default=True,
        )
