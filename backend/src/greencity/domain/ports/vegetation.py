"""Vegetation analysis pipeline port."""

from __future__ import annotations

from typing import Any, Protocol

from greencity.domain.value_objects.vegetation import VegetationResult


class VegetationPipelinePort(Protocol):
    """Compute vegetation coverage for a given multi-band raster array.

    Implementations live in infrastructure (NumPy / Rasterio pipeline).
    Application and domain code depend only on this protocol.
    """

    def run(
        self,
        *,
        red_band: Any,
        nir_band: Any,
        nodata_mask: Any | None = None,
        ndvi_threshold: float = 0.2,
        pixel_size_m: float | None = None,
        transform: Any | None = None,
        crs: str = "EPSG:4326",
        clip_geojson: dict[str, Any] | None = None,
    ) -> VegetationResult:
        """Execute the full pipeline and return a ``VegetationResult``.

        Args:
            red_band: 2-D array of red-band reflectance values.
            nir_band: 2-D array of NIR-band reflectance values.
            nodata_mask: Boolean 2-D array where ``True`` marks nodata pixels.
            ndvi_threshold: NDVI value above which pixels are classified as vegetated.
            pixel_size_m: Ground sampling distance in metres for area statistics.
            transform: Optional affine transform for georeferenced density masks.
            crs: CRS of ``transform`` (density features are reprojected to WGS84).
            clip_geojson: Optional AOI GeoJSON (WGS84) to clip density polygons.

        Returns:
            A fully populated ``VegetationResult``.
        """
        ...
