"""Port for explainable-report narrative generation."""

from __future__ import annotations

from typing import Protocol

from greencity.domain.services.scoring import GreenDeficiencyScore
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.domain.value_objects.report import ExplainableReportContent


class ReportExplainerPort(Protocol):
    """Produce an explainable report from score + indicators.

    Implementations may use templates only, or augment the narrative with
    an LLM. Drivers and recommendations must remain grounded in the GDS
    breakdown (never invented by the model alone).
    """

    def explain(
        self,
        score: GreenDeficiencyScore,
        indicators: IndicatorValues,
        *,
        aoi_name: str = "the study area",
    ) -> ExplainableReportContent:
        """Return structured explainable report content."""
        ...
