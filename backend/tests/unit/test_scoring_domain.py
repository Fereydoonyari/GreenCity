"""Unit tests for Green Deficiency Score domain service."""

from __future__ import annotations

import pytest

from greencity.domain.services.scoring import (
    IndicatorDirection,
    IndicatorRange,
    compute_green_deficiency_score,
    deficiency_component,
    normalise_value,
    rank_neighborhoods,
)
from greencity.domain.value_objects.indicator_weights import IndicatorWeights
from greencity.domain.value_objects.indicators import IndicatorValues


def _weights() -> IndicatorWeights:
    return IndicatorWeights.balanced_default()


def _indicators(
    *,
    vegetation: float = 0.5,
    green_per_m2: float = 0.5,
    road: float = 10_000.0,
    built: float = 0.5,
) -> IndicatorValues:
    return IndicatorValues(
        vegetation_coverage=vegetation,
        green_area_per_m2=green_per_m2,
        road_density=road,
        built_up_ratio=built,
    )


def test_normalise_clamps() -> None:
    r = IndicatorRange(0.0, 100.0)
    assert normalise_value(50.0, r) == pytest.approx(0.5)
    assert normalise_value(-10.0, r) == pytest.approx(0.0)
    assert normalise_value(200.0, r) == pytest.approx(1.0)


def test_deficiency_direction() -> None:
    assert deficiency_component(
        normalised=0.8, direction=IndicatorDirection.BENEFICIAL
    ) == pytest.approx(0.2)
    assert deficiency_component(
        normalised=0.8, direction=IndicatorDirection.PRESSURE
    ) == pytest.approx(0.8)


def test_midpoint_benchmarks_near_fifty() -> None:
    """Mid-range on every indicator ≈ 50 GDS with balanced weights."""

    gds = compute_green_deficiency_score(_indicators(), _weights())
    assert 45.0 <= gds.score <= 55.0
    assert gds.priority_band == "medium"
    assert gds.normalisation == "benchmarks"
    assert len(gds.contributions) == 4


def test_high_green_low_deficiency() -> None:
    lush = _indicators(vegetation=1.0, green_per_m2=1.0, road=0.0, built=0.0)
    barren = _indicators(vegetation=0.0, green_per_m2=0.0, road=20_000.0, built=1.0)
    lush_score = compute_green_deficiency_score(lush, _weights()).score
    barren_score = compute_green_deficiency_score(barren, _weights()).score
    assert lush_score < barren_score
    assert lush_score < 20
    assert barren_score > 80


def test_rank_orders_by_deficiency() -> None:
    better = _indicators(vegetation=0.9, green_per_m2=0.8, road=2_000.0, built=0.1)
    worse = _indicators(vegetation=0.1, green_per_m2=0.05, road=18_000.0, built=0.9)
    ranked = rank_neighborhoods(
        [
            ("north", "North", better),
            ("south", "South", worse),
        ],
        _weights(),
    )
    assert ranked[0].id == "south"
    assert ranked[0].rank == 1
    assert ranked[1].id == "north"
    assert ranked[0].score.score > ranked[1].score.score
