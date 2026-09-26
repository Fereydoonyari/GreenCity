"""LangGraph analysis-agent state definition."""

from __future__ import annotations

from typing import Any, TypedDict


class AnalysisGraphState(TypedDict, total=False):
    """Mutable state flowing through the analysis StateGraph.

    Scientific payloads are stored as plain dicts so the graph stays
    serialisable; the orchestrator reconstitutes domain value objects.
    """

    job_id: str
    aoi_id: str
    scoring_profile_id: str
    vegetation_coverage: float | None
    green_area_m2: float | None
    park_walk_distance_m: float
    current_step: str
    progress_pct: int
    steps_completed: list[str]
    indicators: dict[str, float]
    score: float
    priority_band: str
    normalisation: str
    contributions: list[dict[str, Any]]
    vegetation_source: str
    green_area_source: str
    vegetation_mask: dict | None
    vegetation_hotspot_mask: dict | None
    park_access_mask: dict | None
    heat_exposure_mask: dict | None
    mean_nearest_park_distance_m: float | None
    median_nearest_park_distance_m: float | None
    mean_nearest_park_walk_min: float | None
    median_nearest_park_walk_min: float | None
    mean_lst_c: float | None
    heat_source: str
    summary: str
    aoi_name: str
    report_id: str
    error: str | None
