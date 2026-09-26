"""Hotspot tile masks: low-vegetation and heat-exposure overlays."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from numpy.typing import NDArray

from greencity.infrastructure.imagery.density_mask import MAX_TILE_FEATURES

# Low-vegetation hotspot intensity (lowest NDVI first).
VEG_HOTSPOT_BINS: tuple[tuple[str, float, float, float], ...] = (
    # (class_name, ndvi_max_exclusive, intensity_0_to_1, legend_rank)
    ("critical", 0.10, 1.0, 3),
    ("high", 0.20, 0.7, 2),
    ("elevated", 0.30, 0.4, 1),
)


# Heat exposure relative to AOI LST percentiles (Celsius deltas for legend only).
HEAT_EXPOSURE_BINS: tuple[tuple[str, float, float], ...] = (
    # (class_name, percentile_min_inclusive, intensity)
    ("extreme", 90.0, 1.0),
    ("high", 75.0, 0.75),
    ("elevated", 60.0, 0.5),
)


def build_vegetation_hotspot_mask(
    ndvi: NDArray,
    nodata_mask: NDArray,
    *,
    transform: Any,
    crs: str = "EPSG:4326",
    clip_geojson: dict[str, Any] | None = None,
    tile_size_px: int = 1,
    max_ndvi: float = 0.30,
) -> dict[str, Any]:
    """Tile mask of lowest-vegetation areas (NDVI below ``max_ndvi``).

    Includes bare / built-up pixels and sparse canopy — the planning hotspots
    where green cover is weakest.
    """

    from rasterio.crs import CRS
    from rasterio.transform import Affine

    if transform is None:
        return _empty_hotspot_collection("vegetation")

    affine = transform if isinstance(transform, Affine) else Affine(*transform[:6])
    ndvi_arr = np.asarray(ndvi, dtype=np.float64)
    nodata = np.asarray(nodata_mask, dtype=bool)
    valid = (~nodata) & np.isfinite(ndvi_arr)
    height, width = ndvi_arr.shape

    candidate_count = int((valid & (ndvi_arr < max_ndvi)).sum())
    if candidate_count == 0:
        return _empty_hotspot_collection("vegetation")

    size = _auto_tile_size(tile_size_px, height, width, candidate_count)
    src_crs = CRS.from_user_input(crs) if crs else CRS.from_epsg(4326)

    tiles: list[dict[str, Any]] = []
    for row0 in range(0, height, size):
        row1 = min(row0 + size, height)
        for col0 in range(0, width, size):
            col1 = min(col0 + size, width)
            block = ndvi_arr[row0:row1, col0:col1]
            block_valid = valid[row0:row1, col0:col1]
            if not np.any(block_valid):
                continue
            mean_ndvi = float(np.nanmean(block[block_valid]))
            if not np.isfinite(mean_ndvi) or mean_ndvi >= max_ndvi:
                continue
            class_name, intensity = _veg_hotspot_class(mean_ndvi)
            tiles.append(
                {
                    "row0": row0,
                    "row1": row1,
                    "col0": col0,
                    "col1": col1,
                    "properties": {
                        "hotspot_class": class_name,
                        "intensity": intensity,
                        "mean_ndvi": round(mean_ndvi, 4),
                        "pixel_count": int(block_valid.sum()),
                        "mask_kind": "vegetation_hotspot",
                    },
                }
            )

    return _tiles_to_feature_collection(
        tiles,
        affine=affine,
        crs=src_crs,
        clip_geojson=clip_geojson,
        legend=[
            {"hotspot_class": n, "intensity": inten, "ndvi_max": hi}
            for n, hi, inten, _rank in VEG_HOTSPOT_BINS
        ],
        extra_properties={"mask_kind": "vegetation_hotspot", "tile_size_px": size},
    )


def build_heat_exposure_mask(
    temperature_k: NDArray,
    nodata_mask: NDArray,
    *,
    transform: Any,
    crs: str = "EPSG:4326",
    clip_geojson: dict[str, Any] | None = None,
    tile_size_px: int = 1,
    min_percentile: float = 60.0,
) -> dict[str, Any]:
    """Tile mask of warmest land-surface-temperature areas within an AOI.

    Classes are relative to the AOI's own LST distribution (p60 / p75 / p90)
    so neighbourhood UHI contrasts remain visible across climates.
    """

    from rasterio.crs import CRS
    from rasterio.transform import Affine

    if transform is None:
        return _empty_heat_collection()

    affine = transform if isinstance(transform, Affine) else Affine(*transform[:6])
    kelvin = np.asarray(temperature_k, dtype=np.float64)
    nodata = np.asarray(nodata_mask, dtype=bool)
    valid = (~nodata) & np.isfinite(kelvin)
    if not np.any(valid):
        return _empty_heat_collection()

    celsius = kelvin - 273.15
    vals = celsius[valid]
    p60 = float(np.percentile(vals, 60))
    p75 = float(np.percentile(vals, 75))
    p90 = float(np.percentile(vals, 90))
    mean_c = float(np.mean(vals))
    height, width = kelvin.shape

    candidate = valid & (celsius >= p60) if min_percentile <= 60 else valid & (
        celsius >= float(np.percentile(vals, min_percentile))
    )
    candidate_count = int(candidate.sum())
    if candidate_count == 0:
        return _empty_heat_collection()

    size = _auto_tile_size(tile_size_px, height, width, candidate_count)
    src_crs = CRS.from_user_input(crs) if crs else CRS.from_epsg(4326)

    tiles: list[dict[str, Any]] = []
    for row0 in range(0, height, size):
        row1 = min(row0 + size, height)
        for col0 in range(0, width, size):
            col1 = min(col0 + size, width)
            block = celsius[row0:row1, col0:col1]
            block_valid = valid[row0:row1, col0:col1]
            if not np.any(block_valid):
                continue
            mean_lst = float(np.nanmean(block[block_valid]))
            if not np.isfinite(mean_lst) or mean_lst < p60:
                continue
            class_name, intensity = _heat_class(mean_lst, p60=p60, p75=p75, p90=p90)
            tiles.append(
                {
                    "row0": row0,
                    "row1": row1,
                    "col0": col0,
                    "col1": col1,
                    "properties": {
                        "hotspot_class": class_name,
                        "intensity": intensity,
                        "mean_lst_c": round(mean_lst, 2),
                        "pixel_count": int(block_valid.sum()),
                        "mask_kind": "heat_exposure",
                    },
                }
            )

    return _tiles_to_feature_collection(
        tiles,
        affine=affine,
        crs=src_crs,
        clip_geojson=clip_geojson,
        legend=[
            {"hotspot_class": "elevated", "intensity": 0.5, "percentile_min": 60},
            {"hotspot_class": "high", "intensity": 0.75, "percentile_min": 75},
            {"hotspot_class": "extreme", "intensity": 1.0, "percentile_min": 90},
        ],
        extra_properties={
            "mask_kind": "heat_exposure",
            "tile_size_px": size,
            "mean_lst_c": round(mean_c, 2),
            "thresholds_c": {
                "p60": round(p60, 2),
                "p75": round(p75, 2),
                "p90": round(p90, 2),
            },
        },
    )


def _veg_hotspot_class(mean_ndvi: float) -> tuple[str, float]:
    for name, hi, intensity, _rank in VEG_HOTSPOT_BINS:
        if mean_ndvi < hi:
            return name, intensity
    return "elevated", 0.4


def _heat_class(
    mean_lst_c: float,
    *,
    p60: float,
    p75: float,
    p90: float,
) -> tuple[str, float]:
    if mean_lst_c >= p90:
        return "extreme", 1.0
    if mean_lst_c >= p75:
        return "high", 0.75
    if mean_lst_c >= p60:
        return "elevated", 0.5
    return "elevated", 0.5


def _empty_heat_collection() -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "crs": "EPSG:4326",
            "mask_kind": "heat_exposure",
            "legend": [
                {"hotspot_class": n, "intensity": inten, "percentile_min": pct}
                for n, pct, inten in HEAT_EXPOSURE_BINS
            ],
        },
    }


def _auto_tile_size(tile_size_px: int, height: int, width: int, candidate_count: int) -> int:
    size = max(1, int(tile_size_px))
    while size < max(height, width) and (candidate_count // (size * size) + 1) > MAX_TILE_FEATURES:
        size *= 2
    return size


def _tiles_to_feature_collection(
    tiles: list[dict[str, Any]],
    *,
    affine: Any,
    crs: Any,
    clip_geojson: dict[str, Any] | None,
    legend: list[dict[str, Any]],
    extra_properties: dict[str, Any],
) -> dict[str, Any]:
    from rasterio.warp import transform as rio_xy_transform
    from shapely.geometry import Point, shape

    if not tiles:
        kind = str(extra_properties.get("mask_kind") or "hotspot")
        return _empty_hotspot_collection(kind.replace("_hotspot", ""))

    clip_shape = None
    if clip_geojson is not None:
        try:
            clip_shape = shape(clip_geojson)
            if clip_shape.is_empty:
                clip_shape = None
        except Exception:  # noqa: BLE001
            clip_shape = None

    to_wgs84 = crs.to_epsg() != 4326
    corners_x: list[float] = []
    corners_y: list[float] = []
    for tile in tiles:
        ring_px = (
            (tile["col0"], tile["row0"]),
            (tile["col1"], tile["row0"]),
            (tile["col1"], tile["row1"]),
            (tile["col0"], tile["row1"]),
            (tile["col0"], tile["row0"]),
        )
        for px, py in ring_px:
            x, y = affine * (px, py)
            corners_x.append(float(x))
            corners_y.append(float(y))

    if to_wgs84:
        lons, lats = rio_xy_transform(crs, "EPSG:4326", corners_x, corners_y)
    else:
        lons, lats = corners_x, corners_y

    features_out: list[dict[str, Any]] = []
    for index, tile in enumerate(tiles):
        base = index * 5
        ring = [
            [round(float(lons[base + i]), 7), round(float(lats[base + i]), 7)]
            for i in range(5)
        ]
        if clip_shape is not None:
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
                "properties": tile["properties"],
            }
        )

    payload = {
        "type": "FeatureCollection",
        "features": features_out,
        "properties": {
            "crs": "EPSG:4326",
            "legend": legend,
            **extra_properties,
        },
    }
    return json.loads(json.dumps(payload))


def _empty_hotspot_collection(kind: str) -> dict[str, Any]:
    legend = [
        {"hotspot_class": n, "intensity": inten, "ndvi_max": hi}
        for n, hi, inten, _r in VEG_HOTSPOT_BINS
    ]
    return {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "crs": "EPSG:4326",
            "mask_kind": f"{kind}_hotspot",
            "legend": legend,
        },
    }
