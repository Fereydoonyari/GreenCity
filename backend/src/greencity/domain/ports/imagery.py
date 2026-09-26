"""Port for acquiring Red/NIR satellite imagery for an AOI."""

from __future__ import annotations

from typing import Protocol

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.imagery import RedNirScene


class ImageryAcquisitionPort(Protocol):
    """Fetch Red + NIR bands covering an area of interest.

    Implementations search satellite archives (e.g. NASA HLS via EarthAccess)
    and return arrays ready for the vegetation NDVI pipeline.
    """

    def acquire_red_nir(self, geometry: GeoJsonGeometry) -> RedNirScene:
        """Return a Red/NIR scene clipped to ``geometry``.

        Raises:
            ValidationError / RuntimeError: when no usable scene is found or
            acquisition fails (callers may fall back to OSM proxies).
        """
        ...
