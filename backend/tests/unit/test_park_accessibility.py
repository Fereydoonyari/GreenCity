"""Unit tests for park distance metrics and park-access overlay."""

from __future__ import annotations

import pytest

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
    OsmPark,
)
from greencity.infrastructure.indicators.park_accessibility import (
    BufferParkAccessibility,
    build_park_access_mask,
)


AOI = {
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

PARK_GEOM = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.352, 48.852],
            [2.354, 48.852],
            [2.354, 48.854],
            [2.352, 48.854],
            [2.352, 48.852],
        ]
    ],
}


def _osm(*, parks: tuple[OsmPark, ...] = (), aoi_area: float = 700_000.0) -> OsmContext:
    return OsmContext(
        roads=(),
        parks=parks,
        buildings=(),
        total_road_length_m=0.0,
        total_park_area_m2=sum(p.area_m2 for p in parks),
        total_building_area_m2=0.0,
        aoi_area_m2=aoi_area,
        bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
    )


def test_no_parks_returns_zero() -> None:
    access = BufferParkAccessibility().compute(GeoJsonGeometry(data=AOI), _osm())
    assert access == pytest.approx(0.0)


def test_park_inside_aoi_positive_accessibility() -> None:
    parks = (
        OsmPark(osm_id=1, name="Central", area_m2=10_000.0, geometry=PARK_GEOM),
    )
    access = BufferParkAccessibility().compute(
        GeoJsonGeometry(data=AOI),
        _osm(parks=parks),
        walk_distance_m=300.0,
    )
    assert 0.0 < access <= 1.0


def test_larger_walk_distance_increases_or_equals_access() -> None:
    parks = (
        OsmPark(osm_id=1, name="Central", area_m2=10_000.0, geometry=PARK_GEOM),
    )
    osm = _osm(parks=parks)
    geom = GeoJsonGeometry(data=AOI)
    calc = BufferParkAccessibility()
    near = calc.compute(geom, osm, walk_distance_m=50.0)
    far = calc.compute(geom, osm, walk_distance_m=800.0)
    assert far >= near


def test_compute_metrics_returns_finite_distances() -> None:
    parks = (
        OsmPark(osm_id=1, name="Central", area_m2=10_000.0, geometry=PARK_GEOM),
    )
    metrics = BufferParkAccessibility().compute_metrics(
        GeoJsonGeometry(data=AOI),
        _osm(parks=parks),
        walk_distance_m=300.0,
        sample_step_m=80.0,
    )
    assert metrics.accessibility > 0.0
    assert metrics.park_count == 1
    assert metrics.mean_nearest_park_distance_m == metrics.mean_nearest_park_distance_m
    assert metrics.median_nearest_park_distance_m == metrics.median_nearest_park_distance_m
    assert metrics.mean_nearest_park_distance_m >= 0.0
    assert metrics.mean_nearest_park_walk_min == pytest.approx(
        metrics.mean_nearest_park_distance_m / (5000.0 / 60.0)
    )
    assert metrics.median_nearest_park_walk_min == pytest.approx(
        metrics.median_nearest_park_distance_m / (5000.0 / 60.0)
    )


def test_distance_to_walk_minutes() -> None:
    from greencity.infrastructure.indicators.park_accessibility import (
        distance_to_walk_minutes,
    )

    # 500 m at 5 km/h → 6 minutes
    assert distance_to_walk_minutes(500.0) == pytest.approx(6.0)


def test_park_access_mask_inside_park_is_well_served() -> None:
    """Tiles whose centre lies inside a park must be distance 0 (green), not yellow."""

    parks = (
        OsmPark(osm_id=1, name="Central", area_m2=10_000.0, geometry=PARK_GEOM),
    )
    # AOI tightly around the park so most tile centres fall inside it.
    aoi = {
        "type": "Polygon",
        "coordinates": [
            [
                [2.3515, 48.8515],
                [2.3545, 48.8515],
                [2.3545, 48.8545],
                [2.3515, 48.8545],
                [2.3515, 48.8515],
            ]
        ],
    }
    mask = build_park_access_mask(
        GeoJsonGeometry(data=aoi),
        _osm(parks=parks, aoi_area=50_000.0),
        walk_distance_m=300.0,
        cell_m=40.0,
    )
    assert mask["features"]
    classes = {f["properties"]["hotspot_class"] for f in mask["features"]}
    assert "well_served" in classes
    assert any(f["properties"]["nearest_park_distance_m"] == 0.0 for f in mask["features"])


def test_park_access_mask_has_distance_classes() -> None:
    parks = (
        OsmPark(osm_id=1, name="Central", area_m2=10_000.0, geometry=PARK_GEOM),
    )
    mask = build_park_access_mask(
        GeoJsonGeometry(data=AOI),
        _osm(parks=parks),
        walk_distance_m=300.0,
        cell_m=80.0,
    )
    assert mask["type"] == "FeatureCollection"
    assert mask["properties"]["mask_kind"] == "park_access"
    assert mask["features"]
    classes = {f["properties"]["hotspot_class"] for f in mask["features"]}
    assert classes & {"well_served", "moderate", "underserved"}
    assert "service_area" in (mask.get("properties") or {})
    assert "nearest_park_walk_min" in mask["features"][0]["properties"]
    parks_fc = mask["properties"]["parks"]
    assert parks_fc["type"] == "FeatureCollection"
    assert len(parks_fc["features"]) == 1
    assert parks_fc["features"][0]["properties"]["name"] == "Central"
