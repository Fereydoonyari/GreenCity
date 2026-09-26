"""Unit tests for the Entity base type."""

from greencity.domain.entities.base import Entity


def test_entity_generates_unique_ids() -> None:
    """Each entity instance receives a distinct UUID."""

    first = Entity()
    second = Entity()
    assert first.id != second.id


def test_entity_touch_updates_timestamp() -> None:
    """touch() advances updated_at without changing id."""

    entity = Entity()
    original_updated = entity.updated_at
    entity.touch()
    assert entity.updated_at >= original_updated
