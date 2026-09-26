"""Shared domain entities and base types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class Entity:
    """Base entity with identity and audit timestamps.

    All aggregate roots and entities should inherit from this type so
    identity and lifecycle metadata remain consistent across the domain.
    """

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Update ``updated_at`` to the current UTC time."""

        self.updated_at = datetime.now(UTC)
