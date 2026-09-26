"""Polygon extraction stage: vectorise vegetation masks into GeoJSON polygons.

Converts the raster vegetation classification mask into a list of GeoJSON
Polygon / MultiPolygon features using Shapely geometry operations.  No
Rasterio or file I/O is required—this stage works purely with in-memory
boolean arrays and an optional affine transform for georeferencing.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from shapely.geometry import mapping, shape
from shapely.ops import unary_union


def _array_to_polygons(
    mask: NDArray,
    *,
    pixel_origin: tuple[float, float] = (0.0, 0.0),
    pixel_size: float = 1.0,
    min_pixels: int = 9,
) -> list[Any]:
    """Convert a boolean 2-D mask to a list of Shapely geometries.

    Each contiguous group of ``True`` pixels is turned into a rectangular
    pixel-grid polygon.  Tiny patches below ``min_pixels`` are dropped.

    When georeferencing is needed, pass the raster affine transform via
    ``pixel_origin`` / ``pixel_size``; otherwise the output is in
    pixel-coordinate space.

    Args:
        mask: Boolean mask where ``True`` marks vegetated pixels.
        pixel_origin: (x, y) coordinates of the top-left corner pixel.
        pixel_size: Size of one pixel in the CRS unit.
        min_pixels: Minimum contiguous area in pixels (default 9 = 3×3).
    """
    from shapely.geometry import box

    rows, cols = np.where(mask)
    if len(rows) == 0:
        return []

    # Build one box per vegetated pixel, then dissolve into patches.
    boxes = []
    for r, c in zip(rows.tolist(), cols.tolist()):
        x0 = pixel_origin[0] + c * pixel_size
        y0 = pixel_origin[1] - r * pixel_size  # row 0 = top
        x1 = x0 + pixel_size
        y1 = y0 - pixel_size
        boxes.append(box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    if not boxes:
        return []

    dissolved = unary_union(boxes)
    geoms = list(dissolved.geoms) if hasattr(dissolved, "geoms") else [dissolved]
    return [g for g in geoms if g.area >= min_pixels * pixel_size ** 2]


def extract_vegetation_polygons(
    vegetated_mask: NDArray,
    *,
    pixel_origin: tuple[float, float] = (0.0, 0.0),
    pixel_size: float = 1.0,
    min_pixels: int = 9,
) -> list[dict[str, Any]]:
    """Return a list of GeoJSON geometry dicts for vegetated patches.

    Args:
        vegetated_mask: Boolean mask from :func:`thresholding.threshold_ndvi`.
        pixel_origin: Top-left pixel coordinate (lon, lat or x, y).
        pixel_size: Ground sampling distance per pixel.
        min_pixels: Minimum patch size to include in output.

    Returns:
        List of GeoJSON-serialisable geometry dicts (``type`` + ``coordinates``).
    """
    polygons = _array_to_polygons(
        vegetated_mask,
        pixel_origin=pixel_origin,
        pixel_size=pixel_size,
        min_pixels=min_pixels,
    )
    return [mapping(p) for p in polygons]
