"""Unit tests for IndicatorValues domain assembly."""

from __future__ import annotations

import pytest

from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.indicators import (
    IndicatorValues,
    assemble_indicator_values,
    compute_green_area_per_m2,
)


def test_green_area_per_m2() -> None:
    assert compute_green_area_per_m2(green_area_m2=10_000, aoi_area_m2=50_000) == pytest.approx(
        0.2
    )
    assert compute_green_area_per_m2(green_area_m2=10_000, aoi_area_m2=0) == pytest.approx(0.0)
    assert compute_green_area_per_m2(green_area_m2=80_000, aoi_area_m2=50_000) == pytest.approx(1.0)


def test_assemble_indicators() -> None:
    values = assemble_indicator_values(
        vegetation_coverage=0.4,
        green_area_m2=20_000,
        road_density_m_per_km2=8_000,
        built_up_ratio=0.25,
        aoi_area_m2=100_000,
    )
    assert values.vegetation_coverage == pytest.approx(0.4)
    assert values.green_area_per_m2 == pytest.approx(0.2)
    assert values.road_density == pytest.approx(8_000)
    assert values.built_up_ratio == pytest.approx(0.25)


def test_indicator_values_reject_out_of_range() -> None:
    with pytest.raises(ValidationError):
        IndicatorValues(
            vegetation_coverage=1.5,
            green_area_per_m2=0.1,
            road_density=1.0,
            built_up_ratio=0.1,
        )


def test_as_dict_keys() -> None:
    values = assemble_indicator_values(
        vegetation_coverage=0.1,
        green_area_m2=0,
        road_density_m_per_km2=0,
        built_up_ratio=0.0,
        aoi_area_m2=1_000,
    )
    assert set(values.as_dict()) == {
        "vegetation_coverage",
        "green_area_per_m2",
        "road_density",
        "built_up_ratio",
    }
