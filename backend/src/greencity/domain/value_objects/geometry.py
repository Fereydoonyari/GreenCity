"""Geometry value objects for spatial domain concepts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from greencity.domain.exceptions import ValidationError

ALLOWED_GEOMETRY_TYPES = frozenset({"Polygon", "MultiPolygon"})


@dataclass(frozen=True, slots=True)
class GeoJsonGeometry:
    """A GeoJSON Polygon or MultiPolygon in WGS84 (EPSG:4326).

    Stored as a plain dict so the domain stays free of Shapely / GeoAlchemy.
    Infrastructure adapters convert this to PostGIS geometry.
    """

    data: dict[str, Any]
    srid: int = 4326

    def __post_init__(self) -> None:
        if self.srid != 4326:
            raise ValidationError("Only EPSG:4326 geometries are supported.")
        if not isinstance(self.data, dict):
            raise ValidationError("Geometry must be a GeoJSON object.")
        geom_type = self.data.get("type")
        if geom_type not in ALLOWED_GEOMETRY_TYPES:
            raise ValidationError(
                "Geometry type must be Polygon or MultiPolygon "
                f"(received '{geom_type}')."
            )
        coordinates = self.data.get("coordinates")
        if not coordinates:
            raise ValidationError("Geometry coordinates must not be empty.")
        if geom_type == "Polygon":
            _validate_polygon_rings(coordinates)
        else:
            if not isinstance(coordinates, (list, tuple)) or not coordinates:
                raise ValidationError("MultiPolygon coordinates must be a non-empty list.")
            for polygon in coordinates:
                _validate_polygon_rings(polygon)

    @property
    def geometry_type(self) -> str:
        """Return the GeoJSON geometry type name."""

        return str(self.data["type"])


def _validate_polygon_rings(coordinates: Any) -> None:
    """Ensure polygon coordinates look like a list of linear rings.

    Accepts both ``list`` and ``tuple`` since Shapely's ``mapping()``
    returns tuples when converting geometries back to GeoJSON dicts.
    """

    if not isinstance(coordinates, (list, tuple)) or not coordinates:
        raise ValidationError("Polygon must contain at least one linear ring.")
    exterior = coordinates[0]
    if not isinstance(exterior, (list, tuple)) or len(exterior) < 4:
        raise ValidationError("Polygon exterior ring must have at least 4 positions.")
