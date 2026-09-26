"""Thresholding stage: classify pixels into vegetated / non-vegetated.

Applies a configurable NDVI threshold and returns boolean classification
masks alongside descriptive statistics for the NDVI band.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from greencity.domain.value_objects.vegetation import BandStatistics


def threshold_ndvi(
    ndvi: NDArray,
    nodata_mask: NDArray,
    *,
    threshold: float = 0.2,
) -> tuple[NDArray, NDArray, BandStatistics]:
    """Classify NDVI pixels into vegetated / non-vegetated bins.

    Args:
        ndvi: Float64 NDVI array; NaN where nodata.
        nodata_mask: Boolean mask where ``True`` marks nodata pixels.
        threshold: NDVI value above which a pixel is considered vegetated.
            Typical urban vegetation threshold: 0.2–0.3.

    Returns:
        Tuple ``(vegetated_mask, non_vegetated_mask, ndvi_stats)`` where:
        - Masks are boolean 2-D arrays.
        - ``ndvi_stats`` summarises the valid-pixel distribution.
    """
    valid_ndvi = ndvi[~nodata_mask]
    if valid_ndvi.size == 0:
        stats = BandStatistics(
            minimum=float("nan"),
            maximum=float("nan"),
            mean=float("nan"),
            std=float("nan"),
            valid_pixels=0,
            nodata_pixels=int(nodata_mask.sum()),
        )
        empty = np.zeros(ndvi.shape, dtype=bool)
        return empty, ~nodata_mask, stats

    stats = BandStatistics(
        minimum=float(valid_ndvi.min()),
        maximum=float(valid_ndvi.max()),
        mean=float(valid_ndvi.mean()),
        std=float(valid_ndvi.std()),
        valid_pixels=int(valid_ndvi.size),
        nodata_pixels=int(nodata_mask.sum()),
    )

    vegetated_mask = (~nodata_mask) & (ndvi >= threshold)
    non_vegetated_mask = (~nodata_mask) & (ndvi < threshold)

    return vegetated_mask, non_vegetated_mask, stats
