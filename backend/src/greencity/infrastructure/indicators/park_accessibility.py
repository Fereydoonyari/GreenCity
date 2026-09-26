"""Park accessibility and nearest-park distance metrics from OSM parks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from shapely.geometry import Point, mapping, shape
from shapely.ops import nearest_points, unary_union

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import OsmContext
from greencity.infrastructure.gis import area_m2, geojson_to_shapely
from greencity.infrastructure.imagery.density_mask import MAX_TILE_FEATURES
from greencity.infrastructure.imagery.hotspot_masks import _tiles_to_feature_collection


def _degrees_buffer(distance_m: float, mean_lat: float) -> float:
    """Approximate a metre buffer as degrees at ``mean_lat``."""

    lat_m = 111_320.0
    lon_m = max(111_320.0 * math.cos(math.radians(mean_lat)), 1.0)
    return distance_m / min(lat_m, lon_m)


def _metres_per_degree(mean_lat: float) -> tuple[float, float]:
    lat_m = 111_320.0
    lon_m = max(111_320.0 * math.cos(math.radians(mean_lat)), 1.0)
    return lon_m, lat_m


# Typical urban walking speed (~5 km/h) used to convert distance → time.
WALKING_SPEED_M_PER_MIN = 5000.0 / 60.0  # ≈ 83.3 m/min


def distance_to_walk_minutes(
    distance_m: float,
    *,
    speed_m_per_min: float = WALKING_SPEED_M_PER_MIN,
) -> float:
    """Convert metres to walking minutes at a constant speed."""

    if not math.isfinite(distance_m) or speed_m_per_min <= 0:
        return float("nan")
    return distance_m / speed_m_per_min


@dataclass(frozen=True, slots=True)
class ParkAccessMetrics:
    """Park access enrichment beyond the scored accessibility fraction.

    Distances are Euclidean approximations to OSM park polygons (metres).
    Walking times assume a constant urban walking speed (not network routing).
    """

    accessibility: float
    mean_nearest_park_distance_m: float
    median_nearest_park_distance_m: float
    mean_nearest_park_walk_min: float
    median_nearest_park_walk_min: float
    walk_distance_m: float
    park_count: int
    walking_speed_m_per_min: float = WALKING_SPEED_M_PER_MIN


# Distance classes for the park-access overlay (metres to nearest park).
PARK_DISTANCE_BINS: tuple[tuple[str, float, float], ...] = (
    # (class_name, max_distance_m_exclusive, intensity)
    ("well_served", 300.0, 0.35),
    ("moderate", 600.0, 0.66),
    ("underserved", 1.0e12, 1.0),
)


class BufferParkAccessibility:
    """Park accessibility fraction + nearest-park distance diagnostics.

    Accessibility = AOI ∩ (parks ⊕ walk_distance) / AOI area.
    Distances use an equirectangular metre approximation (urban AOIs).
    """

    def compute(
        self,
        geometry: GeoJsonGeometry,
        osm: OsmContext,
        *,
        walk_distance_m: float = 300.0,
    ) -> float:
        """Return fraction of AOI within ``walk_distance_m`` of any park."""

        return self.compute_metrics(
            geometry, osm, walk_distance_m=walk_distance_m
        ).accessibility

    def compute_metrics(
        self,
        geometry: GeoJsonGeometry,
        osm: OsmContext,
        *,
        walk_distance_m: float = 300.0,
        sample_step_m: float = 60.0,
    ) -> ParkAccessMetrics:
        """Return accessibility fraction and mean/median nearest-park distances."""

        aoi = geojson_to_shapely(geometry)
        if aoi.is_empty or osm.aoi_area_m2 <= 0:
            return _empty_metrics(walk_distance_m, park_count=0)

        park_geoms = _park_shapes(osm)
        if not park_geoms or walk_distance_m <= 0:
            return _empty_metrics(walk_distance_m, park_count=len(park_geoms))

        mean_lat = (aoi.bounds[1] + aoi.bounds[3]) / 2.0
        buf_deg = _degrees_buffer(walk_distance_m, mean_lat)
        buffered = [g.buffer(buf_deg) for g in park_geoms]
        reachable = unary_union(buffered).intersection(aoi)
        accessibility = 0.0
        if not reachable.is_empty:
            accessibility = min(area_m2(reachable) / osm.aoi_area_m2, 1.0)

        distances = _sample_nearest_distances(aoi, park_geoms, sample_step_m=sample_step_m)
        if distances.size == 0:
            mean_d = median_d = float("nan")
        else:
            mean_d = float(np.mean(distances))
            median_d = float(np.median(distances))

        return ParkAccessMetrics(
            accessibility=accessibility,
            mean_nearest_park_distance_m=mean_d,
            median_nearest_park_distance_m=median_d,
            mean_nearest_park_walk_min=distance_to_walk_minutes(mean_d),
            median_nearest_park_walk_min=distance_to_walk_minutes(median_d),
            walk_distance_m=walk_distance_m,
            park_count=len(park_geoms),
        )


def build_park_access_mask(
    geometry: GeoJsonGeometry,
    osm: OsmContext,
    *,
    walk_distance_m: float = 300.0,
    cell_m: float = 60.0,
) -> dict[str, Any]:
    """GeoJSON tiles classified by Euclidean distance to the nearest OSM park.

    Also embeds a ``service_area`` FeatureCollection property describing the
    walk-buffer coverage polygon (when parks exist).
    """

    from rasterio.crs import CRS
    from rasterio.transform import from_bounds

    aoi = geojson_to_shapely(geometry)
    empty = {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "crs": "EPSG:4326",
            "mask_kind": "park_access",
            "legend": [
                {
                    "hotspot_class": n,
                    "max_distance_m": hi if hi < 1e11 else None,
                    "intensity": inten,
                }
                for n, hi, inten in PARK_DISTANCE_BINS
            ],
        },
    }
    if aoi.is_empty:
        return empty

    park_geoms = _park_shapes(osm)
    parks_fc = _parks_feature_collection(osm)
    if not park_geoms:
        # Avoid painting the whole AOI as "underserved" when OSM returned no parks.
        empty = dict(empty)
        empty["properties"] = {**(empty.get("properties") or {}), "parks": parks_fc}
        return empty
    minx, miny, maxx, maxy = aoi.bounds
    mean_lat = (miny + maxy) / 2.0
    lon_m, lat_m = _metres_per_degree(mean_lat)
    cell_lon = cell_m / lon_m
    cell_lat = cell_m / lat_m
    width = max(4, int(math.ceil((maxx - minx) / cell_lon)))
    height = max(4, int(math.ceil((maxy - miny) / cell_lat)))
    while width * height > 20_000:
        cell_lon *= 2
        cell_lat *= 2
        width = max(4, int(math.ceil((maxx - minx) / cell_lon)))
        height = max(4, int(math.ceil((maxy - miny) / cell_lat)))

    affine = from_bounds(minx, miny, maxx, maxy, width, height)
    parks_union = unary_union(park_geoms) if park_geoms else None

    service_area_feature = None
    if parks_union is not None and walk_distance_m > 0:
        buf_deg = _degrees_buffer(walk_distance_m, mean_lat)
        service = parks_union.buffer(buf_deg).intersection(aoi)
        if not service.is_empty:
            service_area_feature = {
                "type": "Feature",
                "geometry": mapping(service),
                "properties": {
                    "mask_kind": "park_service_area",
                    "walk_distance_m": walk_distance_m,
                },
            }

    candidate = height * width
    size = 1
    while size < max(height, width) and (candidate // (size * size) + 1) > MAX_TILE_FEATURES:
        size *= 2

    tiles: list[dict[str, Any]] = []
    for row0 in range(0, height, size):
        row1 = min(row0 + size, height)
        for col0 in range(0, width, size):
            col1 = min(col0 + size, width)
            cx = minx + ((col0 + col1) / 2.0) * (maxx - minx) / width
            cy = maxy - ((row0 + row1) / 2.0) * (maxy - miny) / height
            pt = Point(cx, cy)
            if not aoi.contains(pt) and not aoi.intersects(pt):
                continue
            if parks_union is None or parks_union.is_empty:
                continue
            dist_m = _nearest_park_distance_m(pt, parks_union, lon_m, lat_m)
            class_name, intensity = _park_distance_class(dist_m)
            tiles.append(
                {
                    "row0": row0,
                    "row1": row1,
                    "col0": col0,
                    "col1": col1,
                    "properties": {
                        "hotspot_class": class_name,
                        "intensity": intensity,
                        "nearest_park_distance_m": round(dist_m, 1),
                        "nearest_park_walk_min": round(
                            distance_to_walk_minutes(dist_m), 1
                        ),
                        "mask_kind": "park_access",
                    },
                }
            )

    clip = geometry.data if isinstance(geometry, GeoJsonGeometry) else geometry
    collection = _tiles_to_feature_collection(
        tiles,
        affine=affine,
        crs=CRS.from_epsg(4326),
        clip_geojson=clip,
        legend=[
            {
                "hotspot_class": n,
                "max_distance_m": None if hi > 1e11 else hi,
                "intensity": inten,
            }
            for n, hi, inten in PARK_DISTANCE_BINS
        ],
        extra_properties={
            "mask_kind": "park_access",
            "walk_distance_m": walk_distance_m,
            "walking_speed_m_per_min": round(WALKING_SPEED_M_PER_MIN, 2),
            "tile_size_px": size,
            "parks": parks_fc,
        },
    )
    if service_area_feature is not None:
        props = dict(collection.get("properties") or {})
        props["service_area"] = {
            "type": "FeatureCollection",
            "features": [service_area_feature],
        }
        collection["properties"] = props
    return collection


def _parks_feature_collection(osm: OsmContext) -> dict[str, Any]:
    """GeoJSON FeatureCollection of OSM parks (for map markers / outlines)."""

    features: list[dict[str, Any]] = []
    for park in osm.parks:
        try:
            geom = shape(park.geometry)
        except Exception:  # noqa: BLE001
            continue
        if geom.is_empty:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "osm_id": park.osm_id,
                    "name": park.name or f"Park {park.osm_id}",
                    "area_m2": round(float(park.area_m2), 1),
                    "mask_kind": "park",
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {"mask_kind": "parks", "count": len(features)},
    }


def _empty_metrics(walk_distance_m: float, *, park_count: int) -> ParkAccessMetrics:
    return ParkAccessMetrics(
        accessibility=0.0,
        mean_nearest_park_distance_m=float("nan"),
        median_nearest_park_distance_m=float("nan"),
        mean_nearest_park_walk_min=float("nan"),
        median_nearest_park_walk_min=float("nan"),
        walk_distance_m=walk_distance_m,
        park_count=park_count,
    )


def _park_shapes(osm: OsmContext) -> list[Any]:
    park_geoms = []
    for park in osm.parks:
        try:
            geom = shape(park.geometry)
        except Exception:  # noqa: BLE001
            continue
        if not geom.is_empty:
            park_geoms.append(geom)
    return park_geoms


def _sample_nearest_distances(
    aoi: Any,
    park_geoms: list[Any],
    *,
    sample_step_m: float,
) -> np.ndarray:
    minx, miny, maxx, maxy = aoi.bounds
    mean_lat = (miny + maxy) / 2.0
    lon_m, lat_m = _metres_per_degree(mean_lat)
    step_lon = sample_step_m / lon_m
    step_lat = sample_step_m / lat_m
    parks_union = unary_union(park_geoms)
    dists: list[float] = []
    y = miny + step_lat / 2.0
    while y <= maxy:
        x = minx + step_lon / 2.0
        while x <= maxx:
            pt = Point(x, y)
            if aoi.contains(pt):
                dists.append(_nearest_park_distance_m(pt, parks_union, lon_m, lat_m))
            x += step_lon
        y += step_lat
    return np.asarray(dists, dtype=np.float64)


def _nearest_park_distance_m(
    pt: Point,
    parks_union: Any,
    lon_m: float,
    lat_m: float,
) -> float:
    """Metres to nearest park; ``0`` when the point lies inside a park.

    ``nearest_points`` returns a boundary point even for interior queries, which
    incorrectly inflated distances inside large parks (everything looked yellow).
    """

    if parks_union.covers(pt) or parks_union.contains(pt):
        return 0.0
    nearest = nearest_points(pt, parks_union)[1]
    dx = (pt.x - nearest.x) * lon_m
    dy = (pt.y - nearest.y) * lat_m
    return math.hypot(dx, dy)


def _park_distance_class(distance_m: float) -> tuple[str, float]:
    for name, hi, intensity in PARK_DISTANCE_BINS:
        if distance_m < hi:
            return name, intensity
    return "underserved", 1.0
