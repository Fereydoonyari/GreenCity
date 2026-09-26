"""User aggregate – accounts that own planning projects."""

from __future__ import annotations

from dataclasses import dataclass

from greencity.domain.entities.base import Entity
from greencity.domain.exceptions import ValidationError


@dataclass(kw_only=True)
class User(Entity):
    """Registered user who can create and manage green-planning projects.

    Passwords are never stored in clear text; only ``password_hash`` is kept.
    """

    email: str
    full_name: str
    password_hash: str
    is_active: bool = True

    def __post_init__(self) -> None:
        self.email = self.email.strip().lower()
        self.full_name = self.full_name.strip()
        if not self.email or "@" not in self.email:
            raise ValidationError("User email must be a valid non-empty address.")
        if not self.full_name:
            raise ValidationError("User full name must not be empty.")
        if not self.password_hash:
            raise ValidationError("User password hash must not be empty.")

    def rename(self, full_name: str) -> None:
        """Update the display name and bump ``updated_at``."""

        cleaned = full_name.strip()
        if not cleaned:
            raise ValidationError("User full name must not be empty.")
        self.full_name = cleaned
        self.touch()

    def deactivate(self) -> None:
        """Soft-deactivate the account."""

        self.is_active = False
        self.touch()

    def activate(self) -> None:
        """Re-activate a previously deactivated account."""

        self.is_active = True
        self.touch()
