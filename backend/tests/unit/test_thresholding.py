"""Unit tests for the thresholding pipeline stage."""

from __future__ import annotations

import numpy as np

from greencity.infrastructure.imagery.thresholding import threshold_ndvi


def _ndvi_mask(rows: int = 5, cols: int = 5, ndvi_val: float = 0.3):
    ndvi = np.full((rows, cols), ndvi_val, dtype=np.float64)
    mask = np.zeros((rows, cols), dtype=bool)
    return ndvi, mask


class TestThresholdNdvi:
    def test_all_vegetated(self):
        ndvi, mask = _ndvi_mask(ndvi_val=0.5)
        veg, non_veg, stats = threshold_ndvi(ndvi, mask, threshold=0.2)
        assert veg.all()
        assert not non_veg.any()
        assert stats.valid_pixels == 25
        assert stats.nodata_pixels == 0

    def test_none_vegetated(self):
        ndvi, mask = _ndvi_mask(ndvi_val=0.1)
        veg, non_veg, stats = threshold_ndvi(ndvi, mask, threshold=0.2)
        assert not veg.any()
        assert non_veg.all()

    def test_nodata_excluded_from_both_masks(self):
        ndvi = np.full((3, 3), 0.5)
        nodata = np.zeros((3, 3), dtype=bool)
        nodata[1, 1] = True
        ndvi[1, 1] = np.nan
        veg, non_veg, stats = threshold_ndvi(ndvi, nodata, threshold=0.2)
        assert not veg[1, 1]
        assert not non_veg[1, 1]
        assert stats.nodata_pixels == 1
        assert stats.valid_pixels == 8

    def test_stats_values(self):
        ndvi = np.array([[0.1, 0.5], [0.3, 0.7]], dtype=np.float64)
        mask = np.zeros((2, 2), dtype=bool)
        _, _, stats = threshold_ndvi(ndvi, mask, threshold=0.2)
        np.testing.assert_allclose(stats.mean, ndvi.mean(), atol=1e-9)
        assert stats.minimum == pytest.approx(0.1)
        assert stats.maximum == pytest.approx(0.7)

    def test_all_nodata_returns_empty_masks(self):
        ndvi = np.full((4, 4), np.nan)
        mask = np.ones((4, 4), dtype=bool)
        veg, non_veg, stats = threshold_ndvi(ndvi, mask, threshold=0.2)
        assert not veg.any()
        assert stats.valid_pixels == 0
        assert stats.nodata_pixels == 16


import pytest
