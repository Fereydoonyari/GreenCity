"""Vegetation analysis result value objects."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BandStatistics:
    """Descriptive statistics for a single raster band or computed index.

    All values are in the native unit of the band (reflectance 0-1 for
    surface reflectance data, unitless for NDVI).
    """

    minimum: float
    maximum: float
    mean: float
    std: float
    valid_pixels: int
    nodata_pixels: int


@dataclass(frozen=True, slots=True)
class VegetationCoverage:
    """Per-class pixel counts and coverage fractions for a study area.

    Fractions sum to ``1.0`` across ``vegetated + non_vegetated + nodata``.
    """

    vegetated_pixels: int
    non_vegetated_pixels: int
    nodata_pixels: int
    total_pixels: int
    vegetated_fraction: float
    green_area_m2: float | None = None

    @classmethod
    def from_masks(
        cls,
        vegetated: int,
        non_vegetated: int,
        nodata: int,
        *,
        pixel_area_m2: float | None = None,
    ) -> VegetationCoverage:
        """Build coverage from pixel counts.

        Args:
            vegetated: Pixels classified as vegetated.
            non_vegetated: Pixels classified as bare / built-up.
            nodata: Pixels outside the study boundary or masked.
            pixel_area_m2: Ground area per pixel (m²) for area computation.
        """
        total = vegetated + non_vegetated + nodata
        fraction = vegetated / max(vegetated + non_vegetated, 1)
        green_area = vegetated * pixel_area_m2 if pixel_area_m2 is not None else None
        return cls(
            vegetated_pixels=vegetated,
            non_vegetated_pixels=non_vegetated,
            nodata_pixels=nodata,
            total_pixels=total,
            vegetated_fraction=fraction,
            green_area_m2=green_area,
        )


@dataclass(frozen=True, slots=True)
class VegetationResult:
    """Output of the full vegetation analysis pipeline for one AOI.

    Contains NDVI statistics, coverage summary, and (optionally) a list
    of extracted vegetation polygon footprints as GeoJSON.
    """

    ndvi_stats: BandStatistics
    coverage: VegetationCoverage
    ndvi_threshold: float
    vegetation_polygons: list[dict] = field(default_factory=list)
    crs: str = "EPSG:4326"
    pixel_size_m: float | None = None
    # GeoJSON FeatureCollection of density patches (sparse/moderate/dense).
    density_mask: dict | None = None
    # GeoJSON FeatureCollection of low-NDVI hotspot tiles.
    vegetation_hotspot_mask: dict | None = None
