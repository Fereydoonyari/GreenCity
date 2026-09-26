"""Port for park-accessibility / indicator geometry helpers."""

from __future__ import annotations

from typing import Protocol

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import OsmContext


class ParkAccessibilityPort(Protocol):
    """Compute the share of an AOI within walking distance of parks."""

    def compute(
        self,
        geometry: GeoJsonGeometry,
        osm: OsmContext,
        *,
        walk_distance_m: float = 300.0,
    ) -> float:
        """Return a fraction in [0, 1] of AOI area within ``walk_distance_m`` of a park."""
        ...
