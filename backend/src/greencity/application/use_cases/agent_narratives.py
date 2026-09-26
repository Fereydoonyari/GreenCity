"""Use cases for agentic neighborhood briefs and comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.value_objects.agent_narrative import (
    AgentNarrative,
    CityLocation,
    NeighborhoodSnapshot,
)
from greencity.infrastructure.agent.narratives import NeighborhoodAgentNarrator


def _require_owned_project(uow: UnitOfWork, project_id: UUID, owner_id: UUID) -> None:
    project = uow.projects.get_by_id(project_id)
    if project is None:
        raise NotFoundError(f"Project '{project_id}' was not found.")
    if project.owner_id != owner_id:
        raise ForbiddenError("You do not own this project.")


@dataclass(frozen=True)
class NeighborhoodBriefCommand:
    """Generate a comprehensive agent brief for one neighborhood vs peers."""

    project_id: UUID
    owner_id: UUID
    focus: NeighborhoodSnapshot
    peers: tuple[NeighborhoodSnapshot, ...]


@dataclass(frozen=True)
class NeighborhoodComparisonCommand:
    """Generate an agent comparison across all scored neighborhoods."""

    project_id: UUID
    owner_id: UUID
    neighborhoods: tuple[NeighborhoodSnapshot, ...]


@dataclass(frozen=True)
class VegetationPlanCommand:
    """Generate a geo-aware short/mid/long-term vegetation plan for a neighborhood."""

    project_id: UUID
    owner_id: UUID
    city: CityLocation
    focus: NeighborhoodSnapshot


class GenerateNeighborhoodBriefUseCase:
    """Ownership-checked comprehensive single-neighborhood agent analysis."""

    def __init__(self, uow: UnitOfWork, narrator: NeighborhoodAgentNarrator) -> None:
        self._uow = uow
        self._narrator = narrator

    def execute(self, command: NeighborhoodBriefCommand) -> AgentNarrative:
        _require_owned_project(self._uow, command.project_id, command.owner_id)
        if not command.focus.name.strip():
            raise ValidationError("Focus neighborhood name is required.")
        return self._narrator.neighborhood_brief(command.focus, command.peers)


class GenerateNeighborhoodComparisonUseCase:
    """Ownership-checked agent comparison of all user neighborhoods."""

    def __init__(self, uow: UnitOfWork, narrator: NeighborhoodAgentNarrator) -> None:
        self._uow = uow
        self._narrator = narrator

    def execute(self, command: NeighborhoodComparisonCommand) -> AgentNarrative:
        _require_owned_project(self._uow, command.project_id, command.owner_id)
        if len(command.neighborhoods) < 1:
            raise ValidationError("At least one neighborhood is required.")
        return self._narrator.neighborhood_comparison(command.neighborhoods)


class GenerateVegetationPlanUseCase:
    """Ownership-checked climate-aware vegetation plan for one neighborhood."""

    def __init__(self, uow: UnitOfWork, narrator: NeighborhoodAgentNarrator) -> None:
        self._uow = uow
        self._narrator = narrator

    def execute(self, command: VegetationPlanCommand) -> AgentNarrative:
        _require_owned_project(self._uow, command.project_id, command.owner_id)
        if not command.focus.name.strip():
            raise ValidationError("Focus neighborhood name is required.")
        if not command.city.name.strip():
            raise ValidationError("City name is required.")
        if not -90.0 <= command.city.latitude <= 90.0:
            raise ValidationError("City latitude must be between -90 and 90.")
        if not -180.0 <= command.city.longitude <= 180.0:
            raise ValidationError("City longitude must be between -180 and 180.")
        return self._narrator.vegetation_plan(command.city, command.focus)
