"""Unit tests for the NDVI computation stage."""

from __future__ import annotations

import numpy as np
import pytest

from greencity.infrastructure.imagery.ndvi import compute_ndvi


def _bands(red_val: float, nir_val: float, size: int = 4):
    red = np.full((size, size), red_val, dtype=np.float64)
    nir = np.full((size, size), nir_val, dtype=np.float64)
    return red, nir


class TestComputeNdvi:
    def test_formula(self):
        red, nir = _bands(0.2, 0.6)
        ndvi, _ = compute_ndvi(red, nir)
        expected = (0.6 - 0.2) / (0.6 + 0.2)
        np.testing.assert_allclose(ndvi, expected, atol=1e-9)

    def test_zero_denominator_is_nan(self):
        red = np.array([[0.0, 0.5]])
        nir = np.array([[0.0, 0.5]])
        ndvi, mask = compute_ndvi(red, nir)
        assert np.isnan(ndvi[0, 0])
        assert mask[0, 0]
        assert not np.isnan(ndvi[0, 1])
        assert not mask[0, 1]

    def test_nodata_mask_propagated(self):
        red, nir = _bands(0.3, 0.7)
        input_mask = np.zeros((4, 4), dtype=bool)
        input_mask[0, 0] = True
        ndvi, out_mask = compute_ndvi(red, nir, input_mask)
        assert np.isnan(ndvi[0, 0])
        assert out_mask[0, 0]
        # other pixels unaffected
        assert not out_mask[1, 1]

    def test_range_within_minus1_plus1(self):
        red = np.random.default_rng(42).uniform(0, 0.5, (10, 10))
        nir = np.random.default_rng(0).uniform(0.1, 1.0, (10, 10))
        ndvi, mask = compute_ndvi(red, nir)
        valid = ndvi[~mask]
        assert (valid >= -1.0).all() and (valid <= 1.0).all()
