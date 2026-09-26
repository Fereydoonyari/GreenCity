"""Unit tests for the polygon extraction stage."""

from __future__ import annotations

import numpy as np

from greencity.infrastructure.imagery.polygon_extraction import extract_vegetation_polygons


class TestExtractVegetationPolygons:
    def test_empty_mask_returns_empty_list(self):
        mask = np.zeros((10, 10), dtype=bool)
        result = extract_vegetation_polygons(mask)
        assert result == []

    def test_full_mask_returns_one_polygon(self):
        mask = np.ones((10, 10), dtype=bool)
        result = extract_vegetation_polygons(mask, min_pixels=1)
        assert len(result) >= 1

    def test_result_is_geojson_geometry(self):
        mask = np.ones((5, 5), dtype=bool)
        polygons = extract_vegetation_polygons(mask, min_pixels=1)
        for poly in polygons:
            assert "type" in poly
            assert "coordinates" in poly
            assert poly["type"] in ("Polygon", "MultiPolygon")

    def test_small_patch_filtered_by_min_pixels(self):
        mask = np.zeros((20, 20), dtype=bool)
        mask[0, 0] = True  # single pixel
        result = extract_vegetation_polygons(mask, pixel_size=1.0, min_pixels=9)
        assert result == []

    def test_large_patch_passes_filter(self):
        mask = np.zeros((20, 20), dtype=bool)
        mask[5:10, 5:10] = True  # 25 pixels
        result = extract_vegetation_polygons(mask, pixel_size=1.0, min_pixels=9)
        assert len(result) >= 1
