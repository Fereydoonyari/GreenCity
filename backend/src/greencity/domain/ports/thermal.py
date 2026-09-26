"""Port for acquiring land-surface temperature imagery for an AOI."""

from __future__ import annotations

from typing import Protocol

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.imagery import ThermalScene


class ThermalAcquisitionPort(Protocol):
    """Fetch a surface-temperature raster covering an area of interest.

    Implementations search satellite archives (e.g. Landsat C2 L2 ST via
    EarthAccess) and return Kelvin arrays for heat-exposure overlays.
    """

    def acquire_thermal(self, geometry: GeoJsonGeometry) -> ThermalScene:
        """Return a thermal scene clipped to ``geometry``.

        Raises:
            ValidationError / RuntimeError: when no usable scene is found or
            acquisition fails (callers may skip the heat overlay).
        """
        ...
