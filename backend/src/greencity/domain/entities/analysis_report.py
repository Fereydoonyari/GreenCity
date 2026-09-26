"""Analysis report aggregate – persisted explainable report for a job."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from greencity.domain.entities.base import Entity
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.report import ExplainableReportContent


@dataclass(kw_only=True)
class AnalysisReport(Entity):
    """Persisted explainable report linked to one analysis job."""

    analysis_job_id: UUID
    aoi_id: UUID
    scoring_profile_id: UUID
    headline: str
    executive_summary: str
    priority_band: str
    score: float
    drivers: list[dict[str, Any]]
    recommendations: list[str]
    methodology_notes: str
    source: str = "template"

    def __post_init__(self) -> None:
        self.headline = self.headline.strip()
        self.executive_summary = self.executive_summary.strip()
        self.priority_band = self.priority_band.strip().lower()
        self.methodology_notes = self.methodology_notes.strip()
        self.source = self.source.strip() or "template"
        if not self.headline:
            raise ValidationError("Report headline must not be empty.")
        if not self.executive_summary:
            raise ValidationError("Report executive summary must not be empty.")
        if not 0.0 <= self.score <= 100.0:
            raise ValidationError("Report score must be between 0 and 100.")
        if self.priority_band not in {"low", "medium", "high"}:
            raise ValidationError("priority_band must be low, medium, or high.")

    @classmethod
    def from_content(
        cls,
        *,
        analysis_job_id: UUID,
        aoi_id: UUID,
        scoring_profile_id: UUID,
        content: ExplainableReportContent,
    ) -> AnalysisReport:
        """Create a report entity from structured explainable content."""

        drivers = [
            {
                "key": d.key,
                "label": d.label,
                "raw_value": d.raw_value,
                "weighted_points": d.weighted_points,
                "direction": d.direction.value,
                "explanation": d.explanation,
            }
            for d in content.drivers
        ]
        return cls(
            analysis_job_id=analysis_job_id,
            aoi_id=aoi_id,
            scoring_profile_id=scoring_profile_id,
            headline=content.headline,
            executive_summary=content.executive_summary,
            priority_band=content.priority_band,
            score=content.score,
            drivers=drivers,
            recommendations=list(content.recommendations),
            methodology_notes=content.methodology_notes,
            source=content.source,
        )
