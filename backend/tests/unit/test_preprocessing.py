"""Unit tests for the preprocessing pipeline stage."""

from __future__ import annotations

import numpy as np
import pytest

from greencity.infrastructure.imagery.preprocessing import preprocess_bands


def make_bands(rows: int = 4, cols: int = 4, value: float = 0.5):
    red = np.full((rows, cols), value, dtype=np.float64)
    nir = np.full((rows, cols), value + 0.2, dtype=np.float64)
    return red, nir


class TestPreprocessBands:
    def test_returns_float64(self):
        red, nir = make_bands()
        red_f, nir_f, _ = preprocess_bands(red.astype(np.uint16), nir.astype(np.uint16))
        assert red_f.dtype == np.float64
        assert nir_f.dtype == np.float64

    def test_scale_factor_divides_values(self):
        red = np.array([[10000.0, 5000.0]])
        nir = np.array([[15000.0, 8000.0]])
        red_f, nir_f, _ = preprocess_bands(red, nir, scale_factor=10000.0)
        np.testing.assert_allclose(red_f, [[1.0, 0.5]])
        np.testing.assert_allclose(nir_f, [[1.5, 0.8]])

    def test_fill_value_marks_nodata(self):
        red = np.array([[0.5, -9999.0]])
        nir = np.array([[0.6, 0.6]])
        _, _, mask = preprocess_bands(red, nir, fill_value=-9999.0)
        assert mask[0, 0] is np.bool_(False)
        assert mask[0, 1] is np.bool_(True)

    def test_shape_mismatch_raises(self):
        red = np.zeros((4, 4))
        nir = np.zeros((3, 4))
        with pytest.raises(ValueError, match="shape mismatch"):
            preprocess_bands(red, nir)

    def test_non_2d_raises(self):
        red = np.zeros((4,))
        nir = np.zeros((4,))
        with pytest.raises(ValueError, match="2-D"):
            preprocess_bands(red, nir)

    def test_nodata_mask_all_false_for_clean_data(self):
        red, nir = make_bands()
        _, _, mask = preprocess_bands(red, nir)
        assert not mask.any()
