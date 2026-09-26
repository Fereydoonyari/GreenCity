"""Unit tests for the coverage statistics stage."""

from __future__ import annotations

import numpy as np
import pytest

from greencity.infrastructure.imagery.coverage import compute_coverage


class TestComputeCoverage:
    def _masks(self, veg_count: int, total: int):
        size = total
        veg = np.zeros(size, dtype=bool)
        veg[:veg_count] = True
        non_veg = ~veg
        nodata = np.zeros(size, dtype=bool)
        return veg, non_veg, nodata

    def test_fraction(self):
        veg = np.array([True, True, False, False], dtype=bool)
        non_veg = np.array([False, False, True, True], dtype=bool)
        nodata = np.zeros(4, dtype=bool)
        cov = compute_coverage(veg, non_veg, nodata)
        assert cov.vegetated_fraction == pytest.approx(0.5)

    def test_pixel_counts(self):
        veg = np.array([True, False, False], dtype=bool)
        non_veg = np.array([False, True, False], dtype=bool)
        nodata = np.array([False, False, True], dtype=bool)
        cov = compute_coverage(veg, non_veg, nodata)
        assert cov.vegetated_pixels == 1
        assert cov.non_vegetated_pixels == 1
        assert cov.nodata_pixels == 1
        assert cov.total_pixels == 3

    def test_green_area_computed_when_pixel_size_provided(self):
        veg = np.ones((4, 4), dtype=bool)
        non_veg = np.zeros((4, 4), dtype=bool)
        nodata = np.zeros((4, 4), dtype=bool)
        cov = compute_coverage(veg, non_veg, nodata, pixel_area_m2=100.0)
        assert cov.green_area_m2 == pytest.approx(16 * 100.0)

    def test_green_area_none_when_no_pixel_size(self):
        veg = np.ones((2, 2), dtype=bool)
        non_veg = np.zeros((2, 2), dtype=bool)
        nodata = np.zeros((2, 2), dtype=bool)
        cov = compute_coverage(veg, non_veg, nodata)
        assert cov.green_area_m2 is None
