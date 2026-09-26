"""Shared geometry helpers for OSM adapters.

Uses an equirectangular metres approximation centred on the AOI latitude.
Accurate enough for urban-scale AOIs (a few km) without requiring pyproj.
"""

from __future__ import annotations

import math
from typing import Any

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import BoundingBox


def geojson_to_shapely(geometry: GeoJsonGeometry | dict[str, Any]) -> BaseGeometry:
    """Convert domain/GeoJSON geometry to a Shapely geometry."""

    data = geometry.data if isinstance(geometry, GeoJsonGeometry) else geometry
    return shape(data)


def bounding_box_of(geometry: GeoJsonGeometry | dict[str, Any] | BaseGeometry) -> BoundingBox:
    """Compute the WGS84 bounding box of a geometry."""

    geom = geometry if isinstance(geometry, BaseGeometry) else geojson_to_shapely(geometry)
    min_lon, min_lat, max_lon, max_lat = geom.bounds
    return BoundingBox(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)


def _metres_transform(mean_lat: float):
    """Return a Shapely coordinate transform that maps degrees → local metres."""

    lat_m = 111_320.0
    lon_m = 111_320.0 * math.cos(math.radians(mean_lat))

    def _project(x: float, y: float, z: float | None = None):  # noqa: ARG001
        return (x * lon_m, y * lat_m)

    return _project


def length_m(geom: BaseGeometry) -> float:
    """Approximate geodesic length of a (Multi)LineString in metres."""

    if geom.is_empty:
        return 0.0
    mean_lat = (geom.bounds[1] + geom.bounds[3]) / 2.0
    projected = transform(_metres_transform(mean_lat), geom)
    return float(projected.length)


def area_m2(geom: BaseGeometry) -> float:
    """Approximate geodesic area of a (Multi)Polygon in square metres."""

    if geom.is_empty:
        return 0.0
    mean_lat = (geom.bounds[1] + geom.bounds[3]) / 2.0
    projected = transform(_metres_transform(mean_lat), geom)
    return abs(float(projected.area))


def clip_to_aoi(feature: BaseGeometry, aoi: BaseGeometry) -> BaseGeometry:
    """Return the intersection of ``feature`` with ``aoi`` (empty if none)."""

    if feature.is_empty or aoi.is_empty:
        return feature.__class__()
    try:
        return feature.intersection(aoi)
    except Exception:  # noqa: BLE001 – shapely topology edge cases
        return feature.__class__()


def as_polygon_or_multipolygon(geom: BaseGeometry) -> Polygon | MultiPolygon | None:
    """Extract polygonal parts from an intersection result, if any."""

    if isinstance(geom, (Polygon, MultiPolygon)) and not geom.is_empty:
        return geom
    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon)) and not g.is_empty]
        if not polys:
            return None
        if len(polys) == 1:
            return polys[0]
        return MultiPolygon(
            [p for g in polys for p in (list(g.geoms) if isinstance(g, MultiPolygon) else [g])]
        )
    return None


def to_geojson_dict(geom: BaseGeometry) -> dict[str, Any]:
    """Serialise a Shapely geometry to a plain GeoJSON dict."""

    return mapping(geom)
