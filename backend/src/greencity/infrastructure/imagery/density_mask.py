"""Build a vegetation-density GeoJSON mask from NDVI within vegetated pixels."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from numpy.typing import NDArray

# NDVI bins inside already-vegetated pixels (above classification threshold).
# Higher NDVI ⇒ denser canopy / healthier vegetation.
DENSITY_BINS: tuple[tuple[str, float, float, float], ...] = (
    # (class_name, ndvi_min_inclusive, ndvi_max_exclusive, density_0_to_1)
    ("sparse", 0.0, 0.35, 0.33),
    ("moderate", 0.35, 0.55, 0.66),
    ("dense", 0.55, 1.01, 1.0),
)

# Soft cap so Leaflet stays responsive on large AOIs (raises tile size if needed).
MAX_TILE_FEATURES = 4_000
_MAX_TILE_FEATURES = MAX_TILE_FEATURES  # backwards-compatible alias


def classify_vegetation_density(
    ndvi: NDArray,
    vegetated_mask: NDArray,
) -> NDArray:
    """Return a uint8 density class map (0=none, 1=sparse, 2=moderate, 3=dense)."""

    classes = np.zeros(ndvi.shape, dtype=np.uint8)
    for index, (_name, lo, hi, _density) in enumerate(DENSITY_BINS, start=1):
        classes[vegetated_mask & (ndvi >= lo) & (ndvi < hi)] = index
    return classes


def build_vegetation_density_mask(
    ndvi: NDArray,
    vegetated_mask: NDArray,
    *,
    transform: Any,
    crs: str = "EPSG:4326",
    min_pixels: int = 1,
    clip_geojson: dict[str, Any] | None = None,
    tile_size_px: int = 1,
) -> dict[str, Any]:
    """Vectorise vegetated NDVI into a GeoJSON grid of small square tiles.

    Each tile is a square covering ``tile_size_px × tile_size_px`` source
    pixels (HLS is typically 30 m). Density is the majority class inside the
    tile; ``mean_ndvi`` is the mean of vegetated pixels in that tile.

    Features are in WGS84 (EPSG:4326) for Leaflet. Each feature has:
    - ``density_class``: sparse | moderate | dense
    - ``density``: 0–1 relative density
    - ``mean_ndvi``: mean NDVI inside the tile
    - ``pixel_count``: vegetated pixels contributing to the tile

    When ``clip_geojson`` is provided (AOI in WGS84), tiles whose centre falls
    outside the AOI are dropped.
    """

    from rasterio.crs import CRS
    from rasterio.transform import Affine
    from rasterio.warp import transform as rio_xy_transform
    from shapely.geometry import Point, shape

    if transform is None:
        return {"type": "FeatureCollection", "features": []}

    affine = transform if isinstance(transform, Affine) else Affine(*transform[:6])
    class_map = classify_vegetation_density(ndvi, vegetated_mask)
    height, width = class_map.shape
    src_crs = CRS.from_user_input(crs) if crs else CRS.from_epsg(4326)
    to_wgs84 = src_crs.to_epsg() != 4326

    clip_shape = None
    if clip_geojson is not None:
        try:
            clip_shape = shape(clip_geojson)
            if clip_shape.is_empty:
                clip_shape = None
        except Exception:  # noqa: BLE001
            clip_shape = None

    veg_count = int((class_map > 0).sum())
    if veg_count < max(1, min_pixels):
        return _empty_collection()

    # Auto-bump tile size when the AOI would emit too many Leaflet features.
    size = max(1, int(tile_size_px))
    while size < max(height, width) and (veg_count // (size * size) + 1) > _MAX_TILE_FEATURES:
        size *= 2

    # Collect tile corners in source CRS, then batch-reproject to WGS84.
    corners_x: list[float] = []
    corners_y: list[float] = []
    tile_meta: list[tuple[str, float, float, float, float, int]] = []

    for row0 in range(0, height, size):
        row1 = min(row0 + size, height)
        for col0 in range(0, width, size):
            col1 = min(col0 + size, width)
            block = class_map[row0:row1, col0:col1]
            veg = block > 0
            pixel_count = int(veg.sum())
            if pixel_count < max(1, min_pixels):
                continue

            # Majority density class among vegetated pixels in the tile.
            counts = np.bincount(block[veg].ravel(), minlength=len(DENSITY_BINS) + 1)
            class_id = int(np.argmax(counts[1:])) + 1
            name, lo, hi, density = DENSITY_BINS[class_id - 1]

            mean_ndvi = float(np.nanmean(ndvi[row0:row1, col0:col1][veg]))
            if not np.isfinite(mean_ndvi):
                mean_ndvi = (lo + min(hi, 1.0)) / 2.0

            # Pixel corners: (col, row) in raster space → map coords via Affine.
            # Order: NW, NE, SE, SW, NW (closed ring). Row increases downward.
            ring_px = (
                (col0, row0),
                (col1, row0),
                (col1, row1),
                (col0, row1),
                (col0, row0),
            )
            for px, py in ring_px:
                x, y = affine * (px, py)
                corners_x.append(float(x))
                corners_y.append(float(y))

            tile_meta.append((name, density, mean_ndvi, lo, hi, pixel_count))

    if not tile_meta:
        return _empty_collection()

    if to_wgs84:
        lons, lats = rio_xy_transform(src_crs, "EPSG:4326", corners_x, corners_y)
    else:
        lons, lats = corners_x, corners_y

    features_out: list[dict[str, Any]] = []
    for index, (name, density, mean_ndvi, lo, hi, pixel_count) in enumerate(tile_meta):
        base = index * 5
        ring = [
            [round(float(lons[base + i]), 7), round(float(lats[base + i]), 7)]
            for i in range(5)
        ]
        if clip_shape is not None:
            # Keep tiles whose centre lies inside the AOI.
            cx = (ring[0][0] + ring[2][0]) / 2.0
            cy = (ring[0][1] + ring[2][1]) / 2.0
            if not clip_shape.contains(Point(cx, cy)) and not clip_shape.intersects(
                Point(cx, cy)
            ):
                continue

        features_out.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "density_class": name,
                    "density": density,
                    "mean_ndvi": round(mean_ndvi, 4),
                    "ndvi_min": lo,
                    "ndvi_max": min(hi, 1.0),
                    "pixel_count": pixel_count,
                },
            }
        )

    # Ensure plain JSON types (no numpy scalars).
    return json.loads(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": features_out,
                "properties": {
                    "crs": "EPSG:4326",
                    "tile_size_px": size,
                    "legend": [
                        {
                            "density_class": n,
                            "density": d,
                            "ndvi_min": lo,
                            "ndvi_max": min(hi, 1.0),
                        }
                        for n, lo, hi, d in DENSITY_BINS
                    ],
                },
            }
        )
    )


def _empty_collection() -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "crs": "EPSG:4326",
            "legend": [
                {"density_class": n, "density": d, "ndvi_min": lo, "ndvi_max": min(hi, 1.0)}
                for n, lo, hi, d in DENSITY_BINS
            ],
        },
    }
