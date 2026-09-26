"""Unit tests for Overpass response parsing (no network)."""

from __future__ import annotations

import pytest
from shapely.geometry import Polygon

from greencity.domain.value_objects.urban_context import BoundingBox
from greencity.infrastructure.gis import area_m2
from greencity.infrastructure.osm.parser import parse_overpass_response


AOI = Polygon(
    [
        (2.350, 48.850),
        (2.360, 48.850),
        (2.360, 48.860),
        (2.350, 48.860),
        (2.350, 48.850),
    ]
)
BBOX = BoundingBox(min_lon=2.35, min_lat=48.85, max_lon=2.36, max_lat=48.86)


def _overpass_fixture() -> dict:
    return {
        "elements": [
            {
                "type": "way",
                "id": 101,
                "tags": {"highway": "residential"},
                "geometry": [
                    {"lat": 48.851, "lon": 2.351},
                    {"lat": 48.851, "lon": 2.355},
                    {"lat": 48.851, "lon": 2.359},
                ],
            },
            {
                "type": "way",
                "id": 202,
                "tags": {"leisure": "park", "name": "Square Park"},
                "geometry": [
                    {"lat": 48.852, "lon": 2.352},
                    {"lat": 48.852, "lon": 2.354},
                    {"lat": 48.854, "lon": 2.354},
                    {"lat": 48.854, "lon": 2.352},
                    {"lat": 48.852, "lon": 2.352},
                ],
            },
            {
                "type": "way",
                "id": 303,
                "tags": {"building": "yes"},
                "geometry": [
                    {"lat": 48.855, "lon": 2.353},
                    {"lat": 48.855, "lon": 2.354},
                    {"lat": 48.856, "lon": 2.354},
                    {"lat": 48.856, "lon": 2.353},
                    {"lat": 48.855, "lon": 2.353},
                ],
            },
            # Outside AOI – should be clipped away / empty
            {
                "type": "way",
                "id": 404,
                "tags": {"highway": "primary"},
                "geometry": [
                    {"lat": 49.0, "lon": 3.0},
                    {"lat": 49.0, "lon": 3.1},
                ],
            },
        ]
    }


def test_parse_extracts_roads_parks_buildings() -> None:
    ctx = parse_overpass_response(
        _overpass_fixture(),
        aoi=AOI,
        aoi_area=area_m2(AOI),
        bbox=BBOX,
    )
    assert len(ctx.roads) == 1
    assert ctx.roads[0].highway == "residential"
    assert ctx.total_road_length_m > 0

    assert len(ctx.parks) == 1
    assert ctx.parks[0].name == "Square Park"
    assert ctx.total_park_area_m2 > 0

    assert len(ctx.buildings) == 1
    assert ctx.total_building_area_m2 > 0

    assert ctx.built_up_ratio > 0
    assert ctx.park_coverage_ratio > 0


def test_parse_built_landuse_as_buildings() -> None:
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 707,
                "tags": {"landuse": "residential"},
                "geometry": [
                    {"lat": 48.852, "lon": 2.352},
                    {"lat": 48.852, "lon": 2.354},
                    {"lat": 48.854, "lon": 2.354},
                    {"lat": 48.854, "lon": 2.352},
                    {"lat": 48.852, "lon": 2.352},
                ],
            }
        ]
    }
    ctx = parse_overpass_response(
        payload,
        aoi=AOI,
        aoi_area=area_m2(AOI),
        bbox=BBOX,
    )
    assert len(ctx.buildings) == 1
    assert ctx.built_up_ratio > 0


def test_parse_landuse_relation_members() -> None:
    payload = {
        "elements": [
            {
                "type": "relation",
                "id": 808,
                "tags": {"landuse": "commercial", "type": "multipolygon"},
                "members": [
                    {
                        "type": "way",
                        "role": "outer",
                        "geometry": [
                            {"lat": 48.852, "lon": 2.352},
                            {"lat": 48.852, "lon": 2.354},
                            {"lat": 48.854, "lon": 2.354},
                            {"lat": 48.854, "lon": 2.352},
                            {"lat": 48.852, "lon": 2.352},
                        ],
                    }
                ],
            }
        ]
    }
    ctx = parse_overpass_response(
        payload,
        aoi=AOI,
        aoi_area=area_m2(AOI),
        bbox=BBOX,
    )
    assert len(ctx.buildings) == 1
    assert ctx.built_up_ratio > 0


def test_parse_prefers_building_footprints_over_landuse() -> None:
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"landuse": "residential"},
                "geometry": [
                    {"lat": 48.852, "lon": 2.352},
                    {"lat": 48.852, "lon": 2.354},
                    {"lat": 48.854, "lon": 2.354},
                    {"lat": 48.854, "lon": 2.352},
                    {"lat": 48.852, "lon": 2.352},
                ],
            },
            {
                "type": "way",
                "id": 2,
                "tags": {"building": "yes"},
                "geometry": [
                    {"lat": 48.855, "lon": 2.353},
                    {"lat": 48.855, "lon": 2.354},
                    {"lat": 48.856, "lon": 2.354},
                    {"lat": 48.856, "lon": 2.353},
                    {"lat": 48.855, "lon": 2.353},
                ],
            },
        ]
    }
    ctx = parse_overpass_response(
        payload,
        aoi=AOI,
        aoi_area=area_m2(AOI),
        bbox=BBOX,
    )
    assert len(ctx.buildings) == 1
    assert ctx.buildings[0].osm_id == 2


def test_parse_keeps_nearby_park_outside_aoi() -> None:
    """Parks just outside the AOI must remain for walk-distance metrics."""

    payload = {
        "elements": [
            {
                "type": "way",
                "id": 909,
                "tags": {"leisure": "garden", "name": "Side Garden"},
                # ~200 m east of AOI (AOI ends at lon 2.360)
                "geometry": [
                    {"lat": 48.852, "lon": 2.361},
                    {"lat": 48.852, "lon": 2.363},
                    {"lat": 48.854, "lon": 2.363},
                    {"lat": 48.854, "lon": 2.361},
                    {"lat": 48.852, "lon": 2.361},
                ],
            }
        ]
    }
    ctx = parse_overpass_response(
        payload,
        aoi=AOI,
        aoi_area=area_m2(AOI),
        bbox=BBOX,
    )
    assert len(ctx.parks) == 1
    assert ctx.parks[0].name == "Side Garden"
    # Area inside AOI is zero; geometry is still kept for distance.
    assert ctx.total_park_area_m2 == pytest.approx(0.0)
    ctx = parse_overpass_response(
        {"elements": []},
        aoi=AOI,
        aoi_area=area_m2(AOI),
        bbox=BBOX,
    )
    assert ctx.roads == ()
    assert ctx.parks == ()
    assert ctx.buildings == ()
    assert ctx.total_road_length_m == pytest.approx(0.0)
