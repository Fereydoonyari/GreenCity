"""Unit tests for vegetation / heat hotspot tile masks."""

from __future__ import annotations

import numpy as np
from rasterio.transform import from_origin

from greencity.infrastructure.imagery.hotspot_masks import (
    build_heat_exposure_mask,
    build_vegetation_hotspot_mask,
)
from greencity.infrastructure.imagery.pipeline import NumpyVegetationPipeline


def test_vegetation_hotspot_mask_flags_low_ndvi() -> None:
    ndvi = np.full((10, 10), 0.6, dtype=np.float64)
    ndvi[2:5, 2:5] = 0.05  # critical low vegetation
    nodata = np.zeros_like(ndvi, dtype=bool)
    transform = from_origin(2.35, 48.86, 0.001, 0.001)

    mask = build_vegetation_hotspot_mask(
        ndvi,
        nodata,
        transform=transform,
        crs="EPSG:4326",
        tile_size_px=1,
    )
    assert mask["type"] == "FeatureCollection"
    assert len(mask["features"]) == 9
    assert all(f["properties"]["hotspot_class"] == "critical" for f in mask["features"])
    assert all(f["geometry"]["type"] == "Polygon" for f in mask["features"])


def test_pipeline_emits_vegetation_hotspot_mask() -> None:
    red = np.full((12, 12), 0.4, dtype=np.float64)
    nir = np.full((12, 12), 0.15, dtype=np.float64)  # low NDVI
    transform = from_origin(2.35, 48.86, 0.0005, 0.0005)
    result = NumpyVegetationPipeline().run(
        red_band=red,
        nir_band=nir,
        ndvi_threshold=0.2,
        pixel_size_m=30.0,
        transform=(transform.a, transform.b, transform.c, transform.d, transform.e, transform.f),
        crs="EPSG:4326",
    )
    assert result.vegetation_hotspot_mask is not None
    assert len(result.vegetation_hotspot_mask["features"]) >= 1


def test_heat_exposure_mask_flags_warmest_tiles() -> None:
    # Kelvin: mostly mild, one hot corner
    kelvin = np.full((10, 10), 295.0, dtype=np.float64)  # ~22°C
    kelvin[0:3, 0:3] = 310.0  # ~37°C extreme relative to AOI
    nodata = np.zeros_like(kelvin, dtype=bool)
    transform = from_origin(2.35, 48.86, 0.001, 0.001)

    mask = build_heat_exposure_mask(
        kelvin,
        nodata,
        transform=transform,
        crs="EPSG:4326",
        tile_size_px=1,
    )
    assert mask["type"] == "FeatureCollection"
    assert mask["properties"]["mask_kind"] == "heat_exposure"
    assert len(mask["features"]) >= 1
    assert all(f["properties"]["mask_kind"] == "heat_exposure" for f in mask["features"])
    classes = {f["properties"]["hotspot_class"] for f in mask["features"]}
    assert classes & {"elevated", "high", "extreme"}
