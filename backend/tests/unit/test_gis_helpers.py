"""Unit tests for GIS geometry helpers."""

from __future__ import annotations

import pytest
from shapely.geometry import LineString, Polygon

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.infrastructure.gis import area_m2, bounding_box_of, length_m


SAMPLE = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.35, 48.85],
            [2.36, 48.85],
            [2.36, 48.86],
            [2.35, 48.86],
            [2.35, 48.85],
        ]
    ],
}


def test_bounding_box_of_polygon() -> None:
    bbox = bounding_box_of(GeoJsonGeometry(data=SAMPLE))
    assert bbox.min_lon == pytest.approx(2.35)
    assert bbox.max_lon == pytest.approx(2.36)
    assert bbox.min_lat == pytest.approx(48.85)
    assert bbox.max_lat == pytest.approx(48.86)


def test_area_m2_positive() -> None:
    poly = Polygon([(2.35, 48.85), (2.36, 48.85), (2.36, 48.86), (2.35, 48.86), (2.35, 48.85)])
    assert area_m2(poly) > 100_000  # ~0.7 km²-ish at this latitude for 0.01°×0.01°


def test_length_m_positive() -> None:
    line = LineString([(2.35, 48.85), (2.36, 48.85)])
    assert length_m(line) > 500  # ~740 m at lat 48.85
