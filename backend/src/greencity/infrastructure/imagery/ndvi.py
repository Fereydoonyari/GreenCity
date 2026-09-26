"""NDVI computation stage.

NDVI = (NIR - Red) / (NIR + Red)

Result is in [-1, 1]. Pixels with near-zero denominator (NIR + Red ≈ 0)
are assigned NaN and flagged as nodata.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


_EPSILON = 1e-10


def compute_ndvi(
    red: NDArray,
    nir: NDArray,
    nodata_mask: NDArray | None = None,
) -> tuple[NDArray, NDArray]:
    """Compute NDVI and return an updated nodata mask.

    Args:
        red: Float64 red-band reflectance array.
        nir: Float64 NIR-band reflectance array.
        nodata_mask: Optional boolean mask where ``True`` marks invalid pixels.
            Pixels already masked are preserved; near-zero denominator pixels
            are added to the mask.

    Returns:
        Tuple ``(ndvi, nodata_mask)`` where ``ndvi`` contains NaN for invalid
        pixels and ``nodata_mask`` is the extended mask.
    """
    denominator = nir + red
    # Avoid division by near-zero.
    safe_denom = np.where(np.abs(denominator) < _EPSILON, np.nan, denominator)
    ndvi = (nir - red) / safe_denom

    updated_mask = nodata_mask.copy() if nodata_mask is not None else np.zeros(red.shape, dtype=bool)
    updated_mask |= ~np.isfinite(ndvi)

    # Ensure masked pixels are NaN in the output array.
    ndvi = np.where(updated_mask, np.nan, ndvi)

    return ndvi, updated_mask
