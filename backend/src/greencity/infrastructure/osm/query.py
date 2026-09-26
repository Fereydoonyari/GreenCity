"""Build Overpass QL queries for urban-context features."""

from __future__ import annotations

import math
from collections.abc import Iterator

from greencity.domain.value_objects.urban_context import BoundingBox

# Primary public instance.
DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Global fallbacks tried in parallel with the primary URL.
# Do NOT include regional mirrors (e.g. overpass.osm.ch) — they return empty
# outside their coverage and used to short-circuit analysis with zeros.
OVERPASS_MIRROR_URLS: tuple[str, ...] = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

_BUILT_LANDUSE = (
    "residential|commercial|industrial|retail|construction|garages|railway|"
    "brownfield|education|institutional|military|port|religious|depot"
)

# Include building footprints when the AOI bbox area (deg²) is at or below this.
# ~0.01 ≈ a few km across — fine for neighborhoods, too heavy for whole cities.
_BUILDING_BBOX_AREA_DEG2 = 0.012


def _bb(bbox: BoundingBox) -> str:
    """Overpass bbox order: south,west,north,east."""

    return f"{bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon}"


def _pad_bbox(bbox: BoundingBox, pad_m: float) -> BoundingBox:
    mean_lat = (bbox.min_lat + bbox.max_lat) / 2.0
    lat_pad = pad_m / 111_320.0
    lon_pad = pad_m / max(111_320.0 * math.cos(math.radians(mean_lat)), 1.0)
    return BoundingBox(
        min_lon=bbox.min_lon - lon_pad,
        min_lat=bbox.min_lat - lat_pad,
        max_lon=bbox.max_lon + lon_pad,
        max_lat=bbox.max_lat + lat_pad,
    )


def bbox_area_deg2(bbox: BoundingBox) -> float:
    return max(0.0, (bbox.max_lon - bbox.min_lon) * (bbox.max_lat - bbox.min_lat))


def should_include_buildings(bbox: BoundingBox) -> bool:
    """True when the AOI is small enough for a building-footprint Overpass query."""

    return bbox_area_deg2(bbox) <= _BUILDING_BBOX_AREA_DEG2


def build_urban_context_query(
    bbox: BoundingBox,
    *,
    park_pad_m: float = 800.0,
    timeout_s: int = 45,
    include_buildings: bool | None = None,
) -> str:
    """Roads + parks + built landuse (building footprints fetched separately)."""

    del include_buildings  # kept for call-site compatibility; footprints use build_buildings_query
    bb = _bb(bbox)
    park_bb = _bb(_pad_bbox(bbox, park_pad_m))
    return f"""
[out:json][timeout:{timeout_s}];
(
  way["highway"]({bb});
  way["leisure"~"^(park|garden|nature_reserve|recreation_ground)$"]({park_bb});
  relation["leisure"~"^(park|garden|nature_reserve|recreation_ground)$"]({park_bb});
  way["landuse"~"^(recreation_ground|village_green)$"]({park_bb});
  way["landuse"~"^({_BUILT_LANDUSE})$"]({bb});
  relation["landuse"~"^({_BUILT_LANDUSE})$"]({bb});
);
out geom;
""".strip()


def build_roads_query(bbox: BoundingBox, *, timeout_s: int = 45) -> str:
    """Road-only query (tests / optional split fetch)."""

    return f"""
[out:json][timeout:{timeout_s}];
way["highway"]({_bb(bbox)});
out geom;
""".strip()


def build_parks_query(bbox: BoundingBox, *, park_pad_m: float = 800.0, timeout_s: int = 45) -> str:
    park_bb = _bb(_pad_bbox(bbox, park_pad_m))
    return f"""
[out:json][timeout:{timeout_s}];
(
  way["leisure"~"^(park|garden|nature_reserve|recreation_ground)$"]({park_bb});
  relation["leisure"~"^(park|garden|nature_reserve|recreation_ground)$"]({park_bb});
  way["landuse"~"^(recreation_ground|village_green)$"]({park_bb});
);
out geom;
""".strip()


def build_buildings_query(bbox: BoundingBox, *, timeout_s: int = 45) -> str:
    """Deprecated footprint query — prefer landuse via ``build_built_landuse_query``."""

    return f"""
[out:json][timeout:{timeout_s}];
way["building"]({_bb(bbox)});
out geom;
""".strip()


def build_built_landuse_query(bbox: BoundingBox, *, timeout_s: int = 45) -> str:
    return f"""
[out:json][timeout:{timeout_s}];
(
  way["landuse"~"^({_BUILT_LANDUSE})$"]({_bb(bbox)});
  relation["landuse"~"^({_BUILT_LANDUSE})$"]({_bb(bbox)});
);
out geom;
""".strip()


def iter_bbox_tiles(bbox: BoundingBox, *, max_span_deg: float = 0.03) -> Iterator[BoundingBox]:
    """Split a large bbox into tiles (kept for optional footprint experiments)."""

    lon_span = bbox.max_lon - bbox.min_lon
    lat_span = bbox.max_lat - bbox.min_lat
    if lon_span <= max_span_deg and lat_span <= max_span_deg:
        yield bbox
        return

    n_lon = max(1, math.ceil(lon_span / max_span_deg))
    n_lat = max(1, math.ceil(lat_span / max_span_deg))
    d_lon = lon_span / n_lon
    d_lat = lat_span / n_lat
    for i in range(n_lon):
        for j in range(n_lat):
            yield BoundingBox(
                min_lon=bbox.min_lon + i * d_lon,
                min_lat=bbox.min_lat + j * d_lat,
                max_lon=bbox.min_lon + (i + 1) * d_lon if i + 1 < n_lon else bbox.max_lon,
                max_lat=bbox.min_lat + (j + 1) * d_lat if j + 1 < n_lat else bbox.max_lat,
            )
