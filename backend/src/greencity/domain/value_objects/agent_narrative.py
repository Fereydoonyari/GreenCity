"""Agent narrative value objects for neighborhood briefs and comparisons."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NeighborhoodSnapshot:
    """Scored neighborhood facts grounded for agent narratives (no invented numbers)."""

    id: str
    name: str
    score: float
    priority_band: str
    rank: int | None
    vegetation_coverage: float
    green_area_per_m2: float
    road_density: float
    built_up_ratio: float


@dataclass(frozen=True, slots=True)
class NarrativeSection:
    """One titled section in an agent write-up."""

    title: str
    body: str


@dataclass(frozen=True, slots=True)
class CityLocation:
    """City study-area location used to ground climate-aware planting plans."""

    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class AgentNarrative:
    """Structured agent output for UI display."""

    title: str
    kind: str  # neighborhood_brief | neighborhood_comparison | vegetation_plan
    focus_name: str | None
    sections: tuple[NarrativeSection, ...]
    source: str  # template | llm_augmented
