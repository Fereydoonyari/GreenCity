"""Unit tests for the end-to-end NumpyVegetationPipeline."""

from __future__ import annotations

import numpy as np
import pytest

from greencity.infrastructure.imagery.pipeline import NumpyVegetationPipeline


@pytest.fixture()
def pipeline():
    return NumpyVegetationPipeline()


def _make_bands(rows: int = 10, cols: int = 10, *, veg_fraction: float = 0.5):
    """Synthetic red/NIR arrays where veg_fraction of pixels are vegetated."""
    red = np.full((rows, cols), 0.3, dtype=np.float64)
    nir = np.full((rows, cols), 0.3, dtype=np.float64)
    n_veg = int(rows * cols * veg_fraction)
    # Set vegetated pixels: NDVI = (0.6-0.2)/(0.6+0.2) = 0.5 > 0.2
    red.flat[:n_veg] = 0.2
    nir.flat[:n_veg] = 0.6
    # Non-vegetated: NDVI = 0 < 0.2
    red.flat[n_veg:] = 0.3
    nir.flat[n_veg:] = 0.3
    return red, nir


class TestNumpyVegetationPipeline:
    def test_returns_vegetation_result(self, pipeline):
        from greencity.domain.value_objects.vegetation import VegetationResult

        red, nir = _make_bands()
        result = pipeline.run(red_band=red, nir_band=nir)
        assert isinstance(result, VegetationResult)

    def test_vegetated_fraction_approximate(self, pipeline):
        red, nir = _make_bands(veg_fraction=0.5)
        result = pipeline.run(red_band=red, nir_band=nir)
        assert 0.45 <= result.coverage.vegetated_fraction <= 0.55

    def test_all_vegetated(self, pipeline):
        red, nir = _make_bands(veg_fraction=1.0)
        result = pipeline.run(red_band=red, nir_band=nir)
        assert result.coverage.vegetated_fraction == pytest.approx(1.0)

    def test_no_vegetation(self, pipeline):
        red, nir = _make_bands(veg_fraction=0.0)
        result = pipeline.run(red_band=red, nir_band=nir)
        assert result.coverage.vegetated_fraction == pytest.approx(0.0)

    def test_ndvi_threshold_stored_in_result(self, pipeline):
        red, nir = _make_bands()
        result = pipeline.run(red_band=red, nir_band=nir, ndvi_threshold=0.35)
        assert result.ndvi_threshold == pytest.approx(0.35)

    def test_pixel_size_propagated_to_coverage(self, pipeline):
        red, nir = _make_bands(rows=10, cols=10, veg_fraction=1.0)
        result = pipeline.run(red_band=red, nir_band=nir, pixel_size_m=10.0)
        assert result.coverage.green_area_m2 == pytest.approx(100 * 100.0)

    def test_nodata_mask_excludes_pixels(self, pipeline):
        red, nir = _make_bands(veg_fraction=1.0)
        nodata = np.zeros((10, 10), dtype=bool)
        nodata[0, :] = True  # mask first row
        result = pipeline.run(red_band=red, nir_band=nir, nodata_mask=nodata)
        assert result.coverage.nodata_pixels == 10

    def test_shape_mismatch_raises(self, pipeline):
        red = np.zeros((5, 5))
        nir = np.zeros((4, 5))
        with pytest.raises(ValueError):
            pipeline.run(red_band=red, nir_band=nir)
