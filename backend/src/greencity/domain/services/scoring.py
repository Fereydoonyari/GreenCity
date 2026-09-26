"""Green Deficiency Score domain model and pure scoring functions.

Converts ``IndicatorValues`` + ``IndicatorWeights`` into a
0–100 Green Deficiency Score (GDS) and ranks neighborhoods by priority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.indicator_weights import INDICATOR_KEYS, IndicatorWeights
from greencity.domain.value_objects.indicators import IndicatorValues


class IndicatorDirection(StrEnum):
    """How an indicator contributes to green deficiency."""

    # Higher raw value → lower deficiency (invert after normalisation).
    BENEFICIAL = "beneficial"
    # Higher raw value → higher deficiency.
    PRESSURE = "pressure"


# Directionality is a domain invariant (not configurable per profile).
INDICATOR_DIRECTIONS: dict[str, IndicatorDirection] = {
    "vegetation_coverage": IndicatorDirection.BENEFICIAL,
    "green_area_per_m2": IndicatorDirection.BENEFICIAL,
    "road_density": IndicatorDirection.PRESSURE,
    "built_up_ratio": IndicatorDirection.PRESSURE,
}


@dataclass(frozen=True, slots=True)
class IndicatorRange:
    """Reference [min, max] used to normalise a raw indicator to [0, 1]."""

    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if self.maximum <= self.minimum:
            raise ValidationError("IndicatorRange maximum must be greater than minimum.")


# Urban planning benchmarks for single-AOI scoring (when no cohort exists).
DEFAULT_BENCHMARKS: dict[str, IndicatorRange] = {
    "vegetation_coverage": IndicatorRange(0.0, 1.0),
    "green_area_per_m2": IndicatorRange(0.0, 1.0),
    "road_density": IndicatorRange(0.0, 20_000.0),  # m / km²
    "built_up_ratio": IndicatorRange(0.0, 1.0),
}


@dataclass(frozen=True, slots=True)
class IndicatorContribution:
    """One indicator's contribution to the Green Deficiency Score."""

    key: str
    raw_value: float
    normalised: float
    deficiency_component: float
    weight: float
    weighted_contribution: float
    direction: IndicatorDirection


@dataclass(frozen=True, slots=True)
class GreenDeficiencyScore:
    """Weighted green-deficiency score for one study area (0–100).

    Higher score ⇒ higher priority for green infrastructure investment.
    """

    score: float
    contributions: tuple[IndicatorContribution, ...]
    normalisation: str  # "benchmarks" | "cohort"

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 100.0:
            raise ValidationError("Green Deficiency Score must be between 0 and 100.")

    @property
    def priority_band(self) -> str:
        """Coarse priority label for UI / reports."""

        if self.score >= 70:
            return "high"
        if self.score >= 40:
            return "medium"
        return "low"


@dataclass(frozen=True, slots=True)
class RankedNeighborhood:
    """A scored neighborhood with its rank among peers (1 = highest deficiency)."""

    id: str
    label: str
    rank: int
    score: GreenDeficiencyScore
    indicators: IndicatorValues


def normalise_value(value: float, range_: IndicatorRange) -> float:
    """Clamp-linear normalise ``value`` into [0, 1] using ``range_``."""

    span = range_.maximum - range_.minimum
    normalised = (value - range_.minimum) / span
    return max(0.0, min(1.0, normalised))


def deficiency_component(
    *,
    normalised: float,
    direction: IndicatorDirection,
) -> float:
    """Map a normalised indicator to a deficiency component in [0, 1]."""

    if direction is IndicatorDirection.BENEFICIAL:
        return 1.0 - normalised
    return normalised


def compute_green_deficiency_score(
    indicators: IndicatorValues,
    weights: IndicatorWeights,
    *,
    ranges: dict[str, IndicatorRange] | None = None,
    normalisation: str = "benchmarks",
) -> GreenDeficiencyScore:
    """Compute a 0–100 Green Deficiency Score for one set of indicators.

    Args:
        indicators: Raw measured indicators.
        weights: Relative importance (must sum to 1).
        ranges: Per-indicator [min, max] for normalisation. Defaults to
            ``DEFAULT_BENCHMARKS``.
        normalisation: Label stored on the result (``benchmarks`` or ``cohort``).
    """

    active_ranges = ranges or DEFAULT_BENCHMARKS
    weight_map = weights.as_dict()
    raw = indicators.as_dict()
    contributions: list[IndicatorContribution] = []
    weighted_sum = 0.0

    for key in INDICATOR_KEYS:
        if key not in active_ranges:
            raise ValidationError(f"Missing normalisation range for '{key}'.")
        direction = INDICATOR_DIRECTIONS[key]
        norm = normalise_value(raw[key], active_ranges[key])
        component = deficiency_component(normalised=norm, direction=direction)
        weight = weight_map[key]
        contribution = weight * component
        weighted_sum += contribution
        contributions.append(
            IndicatorContribution(
                key=key,
                raw_value=raw[key],
                normalised=norm,
                deficiency_component=component,
                weight=weight,
                weighted_contribution=contribution,
                direction=direction,
            )
        )

    score = round(weighted_sum * 100.0, 4)
    # Floating-point guard.
    score = max(0.0, min(100.0, score))
    return GreenDeficiencyScore(
        score=score,
        contributions=tuple(contributions),
        normalisation=normalisation,
    )


def _cohort_ranges(items: list[IndicatorValues]) -> dict[str, IndicatorRange]:
    """Build min–max ranges from a cohort of indicator sets."""

    if not items:
        raise ValidationError("Cannot build cohort ranges from an empty list.")
    ranges: dict[str, IndicatorRange] = {}
    for key in INDICATOR_KEYS:
        values = [item.as_dict()[key] for item in items]
        lo, hi = min(values), max(values)
        if hi <= lo:
            # Degenerate cohort: keep a tiny span so normalisation yields 0.5-ish mid.
            hi = lo + 1.0
        ranges[key] = IndicatorRange(minimum=lo, maximum=hi)
    return ranges


def rank_neighborhoods(
    items: list[tuple[str, str, IndicatorValues]],
    weights: IndicatorWeights,
) -> list[RankedNeighborhood]:
    """Score and rank neighborhoods by Green Deficiency Score (desc).

    Args:
        items: List of ``(id, label, indicators)``.
        weights: Scoring profile weights.

    Returns:
        Ranked list (rank 1 = highest deficiency / highest priority).
        Ties keep stable order from the input list after score sort.
    """

    if not items:
        return []

    indicator_list = [indicators for _, _, indicators in items]
    if len(items) == 1:
        ranges = DEFAULT_BENCHMARKS
        normalisation = "benchmarks"
    else:
        ranges = _cohort_ranges(indicator_list)
        normalisation = "cohort"

    scored: list[RankedNeighborhood] = []
    for item_id, label, indicators in items:
        gds = compute_green_deficiency_score(
            indicators,
            weights,
            ranges=ranges,
            normalisation=normalisation,
        )
        scored.append(
            RankedNeighborhood(
                id=item_id,
                label=label,
                rank=0,  # assigned below
                score=gds,
                indicators=indicators,
            )
        )

    scored.sort(key=lambda n: (-n.score.score, n.id))
    return [
        RankedNeighborhood(
            id=n.id,
            label=n.label,
            rank=i,
            score=n.score,
            indicators=n.indicators,
        )
        for i, n in enumerate(scored, start=1)
    ]
