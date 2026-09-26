"""Ports for OpenStreetMap urban-context data providers."""

from __future__ import annotations

from typing import Protocol

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import OsmContext


class OsmDataPort(Protocol):
    """Fetch OSM roads, parks, and buildings intersecting an AOI.

    Implementations live in infrastructure (Overpass API, local cache, …).
    """

    def fetch(self, geometry: GeoJsonGeometry) -> OsmContext:
        """Return urban-context features clipped/summarised for ``geometry``."""
        ...
