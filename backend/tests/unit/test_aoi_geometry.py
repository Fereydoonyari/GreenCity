"""Unit tests for geometry value object and AOI entity."""

import pytest

from greencity.domain.entities.aoi import AreaOfInterest
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from uuid import uuid4

SAMPLE_POLYGON = {
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


def test_geojson_geometry_accepts_polygon() -> None:
    geom = GeoJsonGeometry(data=SAMPLE_POLYGON)
    assert geom.geometry_type == "Polygon"


def test_geojson_geometry_rejects_point() -> None:
    with pytest.raises(ValidationError):
        GeoJsonGeometry(data={"type": "Point", "coordinates": [0, 0]})


def test_aoi_requires_name() -> None:
    with pytest.raises(ValidationError):
        AreaOfInterest(
            project_id=uuid4(),
            name=" ",
            description="",
            geometry=GeoJsonGeometry(data=SAMPLE_POLYGON),
        )
