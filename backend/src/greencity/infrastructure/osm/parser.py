"""Parse Overpass JSON elements into domain OSM value objects."""

from __future__ import annotations

from typing import Any

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmBuilding,
    OsmContext,
    OsmPark,
    OsmRoad,
)
from greencity.infrastructure.gis import (
    area_m2,
    as_polygon_or_multipolygon,
    clip_to_aoi,
    length_m,
    to_geojson_dict,
)


def _coords_from_geometry(geometry: list[dict[str, float]]) -> list[tuple[float, float]]:
    """Convert Overpass ``geometry`` node list to ``(lon, lat)`` pairs."""

    return [(float(node["lon"]), float(node["lat"])) for node in geometry]


def _ring_to_polygon(coords: list[tuple[float, float]]) -> Polygon | None:
    if len(coords) < 3:
        return None
    if coords[0] != coords[-1]:
        coords = [*coords, coords[0]]
    if len(coords) < 4:
        return None
    try:
        poly = Polygon(coords)
    except Exception:  # noqa: BLE001
        return None
    if poly.is_empty:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
        if poly.is_empty:
            return None
    return poly if isinstance(poly, (Polygon, MultiPolygon)) else None


def _way_to_linestring(element: dict[str, Any]) -> LineString | None:
    geometry = element.get("geometry")
    if not geometry or len(geometry) < 2:
        return None
    return LineString(_coords_from_geometry(geometry))


def _way_to_polygon(element: dict[str, Any]) -> Polygon | MultiPolygon | None:
    geometry = element.get("geometry")
    if not geometry or len(geometry) < 4:
        return None
    return _ring_to_polygon(_coords_from_geometry(geometry))


def _relation_to_polygon(element: dict[str, Any]) -> Polygon | MultiPolygon | None:
    """Build a polygon from relation members that carry ``out geom`` coordinates."""

    members = element.get("members") or []
    outers: list[Polygon] = []
    for member in members:
        if member.get("type") != "way":
            continue
        role = member.get("role") or "outer"
        if role not in {"outer", ""}:
            continue
        geometry = member.get("geometry")
        if not geometry or len(geometry) < 4:
            continue
        poly = _ring_to_polygon(_coords_from_geometry(geometry))
        if isinstance(poly, Polygon):
            outers.append(poly)
        elif isinstance(poly, MultiPolygon):
            outers.extend(p for p in poly.geoms if isinstance(p, Polygon))

    if not outers:
        # Some Overpass responses put a flat geometry on the relation itself.
        return _way_to_polygon(element)

    try:
        merged = unary_union(outers)
    except Exception:  # noqa: BLE001
        return None
    if merged.is_empty:
        return None
    if isinstance(merged, (Polygon, MultiPolygon)):
        return merged
    return as_polygon_or_multipolygon(merged)


def _element_to_polygon(element: dict[str, Any]) -> Polygon | MultiPolygon | None:
    if element.get("type") == "relation":
        return _relation_to_polygon(element)
    return _way_to_polygon(element)


def _is_park(tags: dict[str, str]) -> bool:
    leisure = tags.get("leisure")
    if leisure in {"park", "garden", "nature_reserve", "recreation_ground"}:
        return True
    return tags.get("landuse") in {"recreation_ground", "village_green"}


# Keep parks within this distance of the AOI for walk-access metrics.
_PARK_CATCHMENT_M = 800.0


def _park_catchment(aoi: BaseGeometry) -> BaseGeometry:
    """Approximate an 800 m buffer around the AOI in degrees."""

    import math

    minx, miny, maxx, maxy = aoi.bounds
    mean_lat = (miny + maxy) / 2.0
    lat_pad = _PARK_CATCHMENT_M / 111_320.0
    lon_pad = _PARK_CATCHMENT_M / max(111_320.0 * math.cos(math.radians(mean_lat)), 1.0)
    return aoi.buffer(min(lat_pad, lon_pad))


def _is_building(tags: dict[str, str]) -> bool:
    return "building" in tags and tags["building"] not in {"no", "false", "0"}


_BUILT_LANDUSE = {
    "residential",
    "commercial",
    "industrial",
    "retail",
    "construction",
    "garages",
    "railway",
    "brownfield",
    "education",
    "institutional",
    "military",
    "port",
    "religious",
    "depot",
}


def _is_built_landuse(tags: dict[str, str]) -> bool:
    """Coarse built fabric polygons used when footprints are unavailable."""

    return tags.get("landuse") in _BUILT_LANDUSE


def _is_road(tags: dict[str, str]) -> bool:
    highway = tags.get("highway")
    if not highway:
        return False
    return highway not in {
        "footway",
        "path",
        "cycleway",
        "steps",
        "pedestrian",
        "platform",
        "bus_stop",
        "crossing",
        "proposed",
        "construction",
        "abandoned",
        "disused",
        "bridleway",
        "corridor",
        "elevator",
    }


def _append_building(
    buildings: list[OsmBuilding],
    *,
    osm_id: int,
    poly: Polygon | MultiPolygon,
    aoi: BaseGeometry,
) -> None:
    clipped = as_polygon_or_multipolygon(clip_to_aoi(poly, aoi))
    if clipped is None:
        return
    area = area_m2(clipped)
    if area <= 0:
        return
    buildings.append(
        OsmBuilding(
            osm_id=osm_id,
            area_m2=area,
            geometry=to_geojson_dict(clipped),
        )
    )


def parse_overpass_response(
    payload: dict[str, Any],
    *,
    aoi: BaseGeometry,
    aoi_area: float,
    bbox: BoundingBox,
    treat_built_landuse_as_buildings: bool = True,
) -> OsmContext:
    """Convert an Overpass JSON payload into an ``OsmContext``.

    Features are clipped to ``aoi`` before length/area aggregation so metrics
    reflect only the study boundary (not the full bounding-box buffer).

    Building footprints are preferred for built-up ratio; landuse is used only
    when no footprints are present (avoids double-counting).
    """

    elements = payload.get("elements") or []
    roads: list[OsmRoad] = []
    parks: list[OsmPark] = []
    footprints: list[OsmBuilding] = []
    landuse_built: list[OsmBuilding] = []

    for element in elements:
        if element.get("type") not in {"way", "relation"}:
            continue
        tags = element.get("tags") or {}
        osm_id = int(element.get("id", 0))

        if _is_road(tags):
            line = _way_to_linestring(element)
            if line is None:
                continue
            clipped = clip_to_aoi(line, aoi)
            if clipped.is_empty:
                continue
            length = length_m(clipped)
            if length <= 0:
                continue
            roads.append(
                OsmRoad(
                    osm_id=osm_id,
                    highway=str(tags.get("highway", "unknown")),
                    length_m=length,
                    geometry=to_geojson_dict(clipped),
                )
            )
            continue

        if _is_park(tags):
            poly = _element_to_polygon(element)
            if poly is None:
                continue
            catchment = _park_catchment(aoi)
            if poly.is_empty or not poly.intersects(catchment):
                continue
            inside = as_polygon_or_multipolygon(clip_to_aoi(poly, aoi))
            area = area_m2(inside) if inside is not None else 0.0
            access_geom = as_polygon_or_multipolygon(clip_to_aoi(poly, catchment))
            if access_geom is None:
                continue
            name = tags.get("name")
            parks.append(
                OsmPark(
                    osm_id=osm_id,
                    name=str(name) if name else None,
                    area_m2=area,
                    geometry=to_geojson_dict(access_geom),
                )
            )
            continue

        if _is_building(tags):
            poly = _element_to_polygon(element)
            if poly is None:
                continue
            _append_building(footprints, osm_id=osm_id, poly=poly, aoi=aoi)
            continue

        if treat_built_landuse_as_buildings and _is_built_landuse(tags):
            poly = _element_to_polygon(element)
            if poly is None:
                continue
            _append_building(landuse_built, osm_id=osm_id, poly=poly, aoi=aoi)

    buildings = footprints if footprints else landuse_built

    return OsmContext(
        roads=tuple(roads),
        parks=tuple(parks),
        buildings=tuple(buildings),
        total_road_length_m=sum(r.length_m for r in roads),
        total_park_area_m2=sum(p.area_m2 for p in parks),
        total_building_area_m2=sum(b.area_m2 for b in buildings),
        aoi_area_m2=aoi_area,
        bounding_box=bbox,
    )


def empty_osm_context(*, aoi_area: float, bbox: BoundingBox) -> OsmContext:
    """Return an empty context (useful for fakes / empty Overpass responses)."""

    return OsmContext(
        roads=(),
        parks=(),
        buildings=(),
        total_road_length_m=0.0,
        total_park_area_m2=0.0,
        total_building_area_m2=0.0,
        aoi_area_m2=aoi_area,
        bounding_box=bbox,
    )
