"""Unit tests for User and Project domain entities."""

import pytest

from greencity.domain.entities.project import Project, ProjectStatus
from greencity.domain.entities.user import User
from greencity.domain.exceptions import ValidationError
from uuid import uuid4


def test_user_normalizes_email() -> None:
    user = User(email=" Ada@City.GOV ", full_name=" Ada ", password_hash="x")
    assert user.email == "ada@city.gov"
    assert user.full_name == "Ada"


def test_user_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        User(email="a@b.com", full_name="  ", password_hash="x")


def test_project_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        Project(name=" ", description="", owner_id=uuid4())


def test_project_status_transition() -> None:
    project = Project(name="P", description="", owner_id=uuid4())
    project.change_status(ProjectStatus.ACTIVE)
    assert project.status == ProjectStatus.ACTIVE
