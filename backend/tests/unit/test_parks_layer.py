"""Unit tests for parks layer GeoJSON builder (no network)."""

from __future__ import annotations

from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
    OsmPark,
)
from greencity.presentation.api.v1.urban_context import _parks_layer_response


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


def test_parks_layer_tags_inside_and_nearby() -> None:
    inside = OsmPark(
        osm_id=1,
        name="Inside Park",
        area_m2=1000.0,
        geometry={
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
        },
    )
    nearby = OsmPark(
        osm_id=2,
        name="Nearby Park",
        area_m2=0.0,
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [2.361, 48.852],
                    [2.363, 48.852],
                    [2.363, 48.854],
                    [2.361, 48.854],
                    [2.361, 48.852],
                ]
            ],
        },
    )
    ctx = OsmContext(
        roads=(),
        parks=(inside, nearby),
        buildings=(),
        total_road_length_m=0.0,
        total_park_area_m2=1000.0,
        total_building_area_m2=0.0,
        aoi_area_m2=700_000.0,
        bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
    )
    layer = _parks_layer_response(AOI, ctx)
    assert layer.type == "FeatureCollection"
    assert len(layer.features) == 2
    by_name = {f["properties"]["name"]: f["properties"]["location"] for f in layer.features}
    assert by_name["Inside Park"] == "inside"
    assert by_name["Nearby Park"] == "nearby"
    assert layer.properties["inside_count"] == 1
    assert layer.properties["nearby_count"] == 1
    assert "catchment" in layer.properties
