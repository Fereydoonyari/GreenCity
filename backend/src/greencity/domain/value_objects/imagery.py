"""Satellite imagery scene value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RedNirScene:
    """Red + NIR raster arrays clipped to an AOI for NDVI analysis.

    Arrays are opaque to the domain (typically NumPy 2-D float reflectance
    in [0, 1]). Infrastructure owns acquisition and scaling.
    """

    red_band: Any
    nir_band: Any
    nodata_mask: Any | None = None
    pixel_size_m: float = 30.0
    source: str = "hls"
    granule_id: str = ""
    acquired_at: datetime | None = None
    product: str = "HLSS30"
    scale_factor: float = 1.0
    fill_value: float | None = None
    # Affine transform as 6 coeffs (a, b, c, d, e, f) in the raster CRS.
    transform: tuple[float, float, float, float, float, float] | None = None
    crs: str = "EPSG:4326"


@dataclass(frozen=True, slots=True)
class ThermalScene:
    """Land-surface temperature raster clipped to an AOI (Kelvin).

    Arrays are opaque to the domain (typically NumPy 2-D float Kelvin).
    Infrastructure owns acquisition, DN scaling, and fill handling.
    """

    temperature_k: Any
    nodata_mask: Any | None = None
    pixel_size_m: float = 30.0
    source: str = "landsat_st"
    granule_id: str = ""
    acquired_at: datetime | None = None
    product: str = "Landsat_OT_C2_L2"
    scale_factor: float = 0.00341802
    additive_offset: float = 149.0
    fill_value: float | None = 0.0
    transform: tuple[float, float, float, float, float, float] | None = None
    crs: str = "EPSG:4326"

    @property
    def mean_temperature_c(self) -> float | None:
        """Mean valid LST in Celsius, or ``None`` when empty."""

        import numpy as np

        arr = np.asarray(self.temperature_k, dtype=np.float64)
        nodata = (
            np.asarray(self.nodata_mask, dtype=bool)
            if self.nodata_mask is not None
            else ~np.isfinite(arr)
        )
        valid = (~nodata) & np.isfinite(arr)
        if not np.any(valid):
            return None
        return float(np.nanmean(arr[valid]) - 273.15)
