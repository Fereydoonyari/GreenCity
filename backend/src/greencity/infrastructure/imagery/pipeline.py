"""Concrete ``VegetationPipelinePort`` implementation.

Orchestrates the four pipeline stages:

  preprocessing → NDVI computation → thresholding → polygon extraction
                                                   ↘ coverage statistics
                                                   ↘ density mask (optional)
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from greencity.domain.value_objects.vegetation import VegetationResult
from greencity.infrastructure.imagery.coverage import compute_coverage
from greencity.infrastructure.imagery.density_mask import build_vegetation_density_mask
from greencity.infrastructure.imagery.hotspot_masks import build_vegetation_hotspot_mask
from greencity.infrastructure.imagery.ndvi import compute_ndvi
from greencity.infrastructure.imagery.polygon_extraction import extract_vegetation_polygons
from greencity.infrastructure.imagery.preprocessing import preprocess_bands
from greencity.infrastructure.imagery.thresholding import threshold_ndvi


class NumpyVegetationPipeline:
    """NumPy / Shapely / rasterio implementation of the vegetation analysis pipeline.

    Accepts raw band arrays and returns a ``VegetationResult`` without any
    file I/O. When a georeferencing ``transform`` is provided, a density
    GeoJSON mask is also produced for map overlays.
    """

    def __init__(
        self,
        *,
        scale_factor: float = 1.0,
        fill_value: float | None = None,
        min_patch_pixels: int = 9,
    ) -> None:
        self._scale_factor = scale_factor
        self._fill_value = fill_value
        self._min_patch_pixels = min_patch_pixels

    def run(
        self,
        *,
        red_band: Any,
        nir_band: Any,
        nodata_mask: Any | None = None,
        ndvi_threshold: float = 0.2,
        pixel_size_m: float | None = None,
        transform: Any | None = None,
        crs: str = "EPSG:4326",
        clip_geojson: dict[str, Any] | None = None,
    ) -> VegetationResult:
        """Execute all pipeline stages and return a ``VegetationResult``."""

        red_arr: NDArray = np.asarray(red_band, dtype=np.float64)
        nir_arr: NDArray = np.asarray(nir_band, dtype=np.float64)

        red_f, nir_f, nd_mask = preprocess_bands(
            red_arr,
            nir_arr,
            scale_factor=self._scale_factor,
            fill_value=self._fill_value,
        )
        if nodata_mask is not None:
            nd_mask |= np.asarray(nodata_mask, dtype=bool)

        ndvi, nd_mask = compute_ndvi(red_f, nir_f, nd_mask)

        veg_mask, non_veg_mask, ndvi_stats = threshold_ndvi(
            ndvi, nd_mask, threshold=ndvi_threshold
        )

        pixel_area = pixel_size_m**2 if pixel_size_m is not None else None
        coverage = compute_coverage(
            veg_mask, non_veg_mask, nd_mask, pixel_area_m2=pixel_area
        )

        polygons = extract_vegetation_polygons(
            veg_mask,
            pixel_size=pixel_size_m or 1.0,
            min_pixels=self._min_patch_pixels,
        )

        density_mask = None
        vegetation_hotspot_mask = None
        if transform is not None:
            # Match density tiles to low-vegetation hotspot tile size so both
            # overlays share the same grid on the map.
            hotspot_max_ndvi = 0.30
            valid = (~nd_mask) & np.isfinite(ndvi)
            hotspot_candidates = int((valid & (ndvi < hotspot_max_ndvi)).sum())
            height, width = ndvi.shape
            from greencity.infrastructure.imagery.hotspot_masks import _auto_tile_size

            shared_tile_px = _auto_tile_size(
                1, height, width, max(hotspot_candidates, 1)
            )
            density_mask = build_vegetation_density_mask(
                ndvi,
                veg_mask,
                transform=transform,
                crs=crs,
                min_pixels=1,
                clip_geojson=clip_geojson,
                tile_size_px=shared_tile_px,
            )
            vegetation_hotspot_mask = build_vegetation_hotspot_mask(
                ndvi,
                nd_mask,
                transform=transform,
                crs=crs,
                clip_geojson=clip_geojson,
                tile_size_px=shared_tile_px,
                max_ndvi=hotspot_max_ndvi,
            )

        return VegetationResult(
            ndvi_stats=ndvi_stats,
            coverage=coverage,
            ndvi_threshold=ndvi_threshold,
            vegetation_polygons=polygons,
            pixel_size_m=pixel_size_m,
            crs=crs,
            density_mask=density_mask,
            vegetation_hotspot_mask=vegetation_hotspot_mask,
        )
