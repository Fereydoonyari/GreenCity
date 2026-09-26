"""Explainable analysis report value objects and builders."""

from __future__ import annotations

from dataclasses import dataclass, field

from greencity.domain.exceptions import ValidationError
from greencity.domain.services.scoring import (
    INDICATOR_DIRECTIONS,
    GreenDeficiencyScore,
    IndicatorContribution,
    IndicatorDirection,
)
from greencity.domain.value_objects.indicators import IndicatorValues

# Human-readable labels for report text.
INDICATOR_LABELS: dict[str, str] = {
    "vegetation_coverage": "vegetation coverage",
    "green_area_per_m2": "green area per m²",
    "road_density": "road density",
    "built_up_ratio": "built-up ratio",
}

# Deterministic planning recommendations keyed by indicator.
_RECOMMENDATIONS: dict[str, str] = {
    "vegetation_coverage": (
        "Expand tree canopy and vegetated surfaces (street trees, green roofs, "
        "pocket parks) where NDVI / vegetation coverage is lowest."
    ),
    "green_area_per_m2": (
        "Increase the share of land covered by parks and green open space "
        "where green area per square metre of the study area is lowest."
    ),
    "road_density": (
        "Introduce green corridors and traffic-calming along dense road networks "
        "to reduce sealed surface impacts and improve microclimate."
    ),
    "built_up_ratio": (
        "Prioritise retrofit greening in highly built-up fabric (courtyards, "
        "facades, rooftops) where new land is scarce."
    ),
}


@dataclass(frozen=True, slots=True)
class DriverExplanation:
    """One indicator explained as a driver of green deficiency."""

    key: str
    label: str
    raw_value: float
    weighted_points: float  # contribution × 100 (score points)
    direction: IndicatorDirection
    explanation: str


@dataclass(frozen=True, slots=True)
class ExplainableReportContent:
    """Structured explainable report body (not yet persisted)."""

    headline: str
    executive_summary: str
    priority_band: str
    score: float
    drivers: tuple[DriverExplanation, ...]
    recommendations: tuple[str, ...]
    methodology_notes: str
    source: str = "template"  # template | llm_augmented

    def __post_init__(self) -> None:
        if not self.headline.strip():
            raise ValidationError("Report headline must not be empty.")
        if not self.executive_summary.strip():
            raise ValidationError("Report executive summary must not be empty.")
        if not 0.0 <= self.score <= 100.0:
            raise ValidationError("Report score must be between 0 and 100.")


def _driver_explanation(contribution: IndicatorContribution) -> DriverExplanation:
    label = INDICATOR_LABELS.get(contribution.key, contribution.key)
    points = contribution.weighted_contribution * 100.0
    if contribution.direction is IndicatorDirection.BENEFICIAL:
        text = (
            f"{label.capitalize()} is relatively weak "
            f"(raw={contribution.raw_value:.3g}), contributing "
            f"{points:.1f} points to the deficiency score."
        )
    else:
        text = (
            f"{label.capitalize()} is relatively high "
            f"(raw={contribution.raw_value:.3g}), contributing "
            f"{points:.1f} points to the deficiency score."
        )
    return DriverExplanation(
        key=contribution.key,
        label=label,
        raw_value=contribution.raw_value,
        weighted_points=points,
        direction=contribution.direction,
        explanation=text,
    )


def _recommendations_for(drivers: list[DriverExplanation], *, limit: int = 3) -> tuple[str, ...]:
    recs: list[str] = []
    for driver in drivers[:limit]:
        rec = _RECOMMENDATIONS.get(driver.key)
        if rec and rec not in recs:
            recs.append(rec)
    if not recs:
        recs.append(
            "Maintain monitoring of green indicators and revisit scoring weights "
            "with stakeholders before major capital investment."
        )
    return tuple(recs)


def build_explainable_report(
    score: GreenDeficiencyScore,
    indicators: IndicatorValues,
    *,
    aoi_name: str = "the study area",
    narrative_override: str | None = None,
    source: str = "template",
) -> ExplainableReportContent:
    """Build a structured explainable report from a GDS breakdown.

    Pure domain function. Optional ``narrative_override`` lets an LLM enrich
    the executive summary without changing drivers or recommendations.
    """

    ordered = sorted(
        score.contributions,
        key=lambda c: c.weighted_contribution,
        reverse=True,
    )
    drivers = tuple(_driver_explanation(c) for c in ordered)
    top = drivers[:3]
    recommendations = _recommendations_for(list(drivers))

    headline = (
        f"{aoi_name}: Green Deficiency Score {score.score:.1f}/100 "
        f"({score.priority_band} priority)"
    )

    driver_bits = "; ".join(
        f"{d.label} ({d.weighted_points:.1f} pts)" for d in top
    )
    default_summary = (
        f"Analysis of {aoi_name} yields a Green Deficiency Score of "
        f"{score.score:.1f} out of 100, placing it in the "
        f"{score.priority_band} priority band for green infrastructure. "
        f"The strongest drivers are: {driver_bits}. "
        f"Vegetation coverage is {indicators.vegetation_coverage:.1%}, "
        f"green area per m² {indicators.green_area_per_m2:.1%}, "
        f"and built-up ratio {indicators.built_up_ratio:.1%}."
    )

    methodology = (
        "Indicators are normalised against urban benchmarks, converted to "
        "deficiency components (beneficial indicators are inverted), then "
        "combined with the scoring-profile weights into a 0–100 Green "
        "Deficiency Score. Higher scores indicate higher priority for "
        "green investment. Directions: "
        + ", ".join(
            f"{INDICATOR_LABELS.get(k, k)}={d.value}"
            for k, d in INDICATOR_DIRECTIONS.items()
        )
        + f". Normalisation mode: {score.normalisation}."
    )

    return ExplainableReportContent(
        headline=headline,
        executive_summary=(narrative_override or default_summary).strip(),
        priority_band=score.priority_band,
        score=score.score,
        drivers=drivers,
        recommendations=recommendations,
        methodology_notes=methodology,
        source=source,
    )
