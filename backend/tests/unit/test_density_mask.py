"""Unit tests for vegetation density mask extraction."""

from __future__ import annotations

import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import shape

from greencity.infrastructure.imagery.density_mask import (
    build_vegetation_density_mask,
    classify_vegetation_density,
)
from greencity.infrastructure.imagery.pipeline import NumpyVegetationPipeline


def test_classify_vegetation_density_bins() -> None:
    ndvi = np.array(
        [
            [0.1, 0.25, 0.45, 0.7],
            [0.15, 0.3, 0.5, 0.8],
        ],
        dtype=np.float64,
    )
    vegetated = ndvi >= 0.2
    classes = classify_vegetation_density(ndvi, vegetated)
    assert classes[0, 0] == 0  # below vegetation threshold → not vegetated class
    assert classes[0, 1] == 1  # sparse
    assert classes[0, 2] == 2  # moderate
    assert classes[0, 3] == 3  # dense


def test_build_vegetation_density_mask_emits_pixel_tiles() -> None:
    ndvi = np.full((12, 12), 0.5, dtype=np.float64)
    ndvi[2:6, 2:6] = 0.75  # dense patch
    ndvi[7:10, 7:10] = 0.28  # sparse patch
    vegetated = ndvi >= 0.2
    transform = from_origin(2.35, 48.86, 0.001, 0.001)

    mask = build_vegetation_density_mask(
        ndvi,
        vegetated,
        transform=transform,
        crs="EPSG:4326",
        min_pixels=1,
        tile_size_px=1,
    )
    assert mask["type"] == "FeatureCollection"
    # One small square per vegetated pixel (not one dissolved blob per class).
    assert len(mask["features"]) == int(vegetated.sum())
    classes = {f["properties"]["density_class"] for f in mask["features"]}
    assert "dense" in classes
    assert "sparse" in classes
    assert "moderate" in classes
    for feature in mask["features"]:
        assert feature["geometry"]["type"] == "Polygon"
        ring = feature["geometry"]["coordinates"][0]
        assert len(ring) == 5
        assert 0 < feature["properties"]["density"] <= 1
        assert feature["properties"]["pixel_count"] >= 1


def test_tile_size_aggregates_blocks() -> None:
    ndvi = np.full((8, 8), 0.6, dtype=np.float64)
    vegetated = ndvi >= 0.2
    transform = from_origin(2.35, 48.86, 0.001, 0.001)
    mask = build_vegetation_density_mask(
        ndvi,
        vegetated,
        transform=transform,
        crs="EPSG:4326",
        tile_size_px=2,
    )
    # 8x8 with 2x2 tiles → 16 features
    assert len(mask["features"]) == 16
    assert mask["properties"]["tile_size_px"] == 2
    assert all(f["properties"]["pixel_count"] == 4 for f in mask["features"])


def test_speckled_vegetation_is_not_dropped() -> None:
    """Urban canopy is often 1-pixel islands at 30 m — must still appear."""

    ndvi = np.zeros((16, 16), dtype=np.float64)
    ndvi[::2, ::2] = 0.45
    vegetated = ndvi >= 0.2
    transform = from_origin(500_000.0, 5_400_000.0, 30.0, 30.0)
    mask = build_vegetation_density_mask(
        ndvi,
        vegetated,
        transform=transform,
        crs="EPSG:32631",
        min_pixels=1,
    )
    assert len(mask["features"]) == int(vegetated.sum())
    ring = mask["features"][0]["geometry"]["coordinates"][0]
    lon, lat = ring[0]
    assert -180 <= lon <= 180
    assert -90 <= lat <= 90


def test_build_vegetation_density_mask_clips_to_aoi() -> None:
    ndvi = np.full((20, 20), 0.6, dtype=np.float64)
    vegetated = ndvi >= 0.2
    transform = from_origin(2.35, 48.86, 0.001, 0.001)
    clip = {
        "type": "Polygon",
        "coordinates": [
            [
                [2.35, 48.85],
                [2.352, 48.85],
                [2.352, 48.852],
                [2.35, 48.852],
                [2.35, 48.85],
            ]
        ],
    }
    mask = build_vegetation_density_mask(
        ndvi,
        vegetated,
        transform=transform,
        crs="EPSG:4326",
        clip_geojson=clip,
    )
    assert len(mask["features"]) >= 1
    assert len(mask["features"]) < int(vegetated.sum())
    clip_shape = shape(clip)
    for feature in mask["features"]:
        geom = shape(feature["geometry"])
        assert geom.centroid.within(clip_shape.buffer(1e-6)) or geom.intersects(clip_shape)


def test_pipeline_emits_density_mask_with_transform() -> None:
    red = np.full((16, 16), 0.1, dtype=np.float64)
    nir = np.full((16, 16), 0.55, dtype=np.float64)
    transform = from_origin(2.35, 48.86, 0.0005, 0.0005)
    result = NumpyVegetationPipeline().run(
        red_band=red,
        nir_band=nir,
        ndvi_threshold=0.2,
        pixel_size_m=30.0,
        transform=(transform.a, transform.b, transform.c, transform.d, transform.e, transform.f),
        crs="EPSG:4326",
    )
    assert result.density_mask is not None
    assert result.density_mask["type"] == "FeatureCollection"
    assert len(result.density_mask["features"]) >= 1
    assert all(f["geometry"]["type"] == "Polygon" for f in result.density_mask["features"])
