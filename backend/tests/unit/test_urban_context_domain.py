"""Unit tests for urban-context domain value objects."""

from __future__ import annotations

import pytest

from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmBuilding,
    OsmContext,
    OsmPark,
    OsmRoad,
)


def _bbox() -> BoundingBox:
    return BoundingBox(min_lon=2.3, min_lat=48.8, max_lon=2.4, max_lat=48.9)


def test_bounding_box_rejects_inverted() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(min_lon=2.4, min_lat=48.8, max_lon=2.3, max_lat=48.9)


def test_osm_context_ratios() -> None:
    ctx = OsmContext(
        roads=(
            OsmRoad(
                osm_id=1,
                highway="residential",
                length_m=500.0,
                geometry={"type": "LineString", "coordinates": []},
            ),
        ),
        parks=(
            OsmPark(
                osm_id=2,
                name="Park",
                area_m2=10_000.0,
                geometry={"type": "Polygon", "coordinates": []},
            ),
        ),
        buildings=(
            OsmBuilding(
                osm_id=3,
                area_m2=2_000.0,
                geometry={"type": "Polygon", "coordinates": []},
            ),
        ),
        total_road_length_m=500.0,
        total_park_area_m2=10_000.0,
        total_building_area_m2=2_000.0,
        aoi_area_m2=100_000.0,  # 0.1 km²
        bounding_box=_bbox(),
    )
    assert ctx.road_density_m_per_km2 == pytest.approx(5_000.0)
    assert ctx.built_up_ratio == pytest.approx(0.02)
    assert ctx.park_coverage_ratio == pytest.approx(0.1)
