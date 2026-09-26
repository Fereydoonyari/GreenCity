"""Preprocessing stage: validate and normalise band arrays.

Converts integer DN values to float reflectance in [0, 1] when a scale
factor is provided, replaces fill values with NaN, and enforces shape
consistency between bands.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def preprocess_bands(
    red: NDArray,
    nir: NDArray,
    *,
    scale_factor: float = 1.0,
    fill_value: float | None = None,
) -> tuple[NDArray, NDArray, NDArray]:
    """Validate, scale, and align red and NIR bands.

    Args:
        red: 2-D array of red-band values (DN or reflectance).
        nir: 2-D array of NIR-band values (DN or reflectance).
        scale_factor: Divide raw DNs by this value to get reflectance.
            Use ``1.0`` if data are already in [0, 1].
        fill_value: Pixel value that denotes missing / nodata data.
            Such pixels are marked in the returned mask.

    Returns:
        Tuple ``(red_f, nir_f, nodata_mask)`` where:
        - ``red_f`` / ``nir_f`` are float64 arrays in [0, 1].
        - ``nodata_mask`` is a boolean array, ``True`` where data is invalid.

    Raises:
        ValueError: If band shapes differ or arrays are not 2-D.
    """
    if red.ndim != 2 or nir.ndim != 2:
        raise ValueError("Band arrays must be 2-D.")
    if red.shape != nir.shape:
        raise ValueError(
            f"Band shape mismatch: red={red.shape}, nir={nir.shape}."
        )

    red_f = red.astype(np.float64) / scale_factor
    nir_f = nir.astype(np.float64) / scale_factor

    nodata_mask = np.zeros(red.shape, dtype=bool)
    if fill_value is not None:
        nodata_mask |= (red == fill_value) | (nir == fill_value)

    # Mark physically impossible reflectance as nodata.
    nodata_mask |= ~np.isfinite(red_f) | ~np.isfinite(nir_f)

    return red_f, nir_f, nodata_mask
