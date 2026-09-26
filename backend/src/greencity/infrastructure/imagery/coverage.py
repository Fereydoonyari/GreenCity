"""Coverage statistics stage.

Aggregates pixel counts from the classification masks into a
``VegetationCoverage`` value object, optionally converting pixel
counts to ground area using the pixel ground sampling distance.
"""

from __future__ import annotations

from numpy.typing import NDArray

from greencity.domain.value_objects.vegetation import VegetationCoverage


def compute_coverage(
    vegetated_mask: NDArray,
    non_vegetated_mask: NDArray,
    nodata_mask: NDArray,
    *,
    pixel_area_m2: float | None = None,
) -> VegetationCoverage:
    """Build a ``VegetationCoverage`` summary from classification masks.

    Args:
        vegetated_mask: Boolean mask for vegetated pixels.
        non_vegetated_mask: Boolean mask for non-vegetated pixels.
        nodata_mask: Boolean mask for nodata / out-of-extent pixels.
        pixel_area_m2: Ground area per pixel in m².  When provided, the
            green area in m² is included in the result.

    Returns:
        Populated ``VegetationCoverage`` value object.
    """
    return VegetationCoverage.from_masks(
        vegetated=int(vegetated_mask.sum()),
        non_vegetated=int(non_vegetated_mask.sum()),
        nodata=int(nodata_mask.sum()),
        pixel_area_m2=pixel_area_m2,
    )
