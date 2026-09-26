"""Analysis orchestration result value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.services.scoring import GreenDeficiencyScore
from greencity.domain.value_objects.indicators import IndicatorValues


@dataclass(frozen=True, slots=True)
class AnalysisOrchestrationResult:
    """Outcome of a full analysis-job orchestration run.

    Scientific values come from use cases / domain services. ``summary`` is
    the report executive summary; ``report`` is the persisted explainable
    report when generation succeeded.
    """

    job_id: UUID
    aoi_id: UUID
    scoring_profile_id: UUID
    indicators: IndicatorValues
    score: GreenDeficiencyScore
    steps_completed: tuple[str, ...] = field(default_factory=tuple)
    summary: str = ""
    vegetation_source: str = ""
    green_area_source: str = ""
    report: AnalysisReport | None = None
    vegetation_mask: dict | None = None
    vegetation_hotspot_mask: dict | None = None
    park_access_mask: dict | None = None
    heat_exposure_mask: dict | None = None
    mean_nearest_park_distance_m: float | None = None
    median_nearest_park_distance_m: float | None = None
    mean_nearest_park_walk_min: float | None = None
    median_nearest_park_walk_min: float | None = None
    mean_lst_c: float | None = None
    heat_source: str = ""
