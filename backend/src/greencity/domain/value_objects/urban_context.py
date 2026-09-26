"""Urban context value objects: OSM roads, parks, and buildings.

Used for road density, built-up ratio, and park-coverage proxies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from greencity.domain.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Axis-aligned WGS84 bounding box (min_lon, min_lat, max_lon, max_lat)."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def __post_init__(self) -> None:
        if self.min_lon >= self.max_lon or self.min_lat >= self.max_lat:
            raise ValidationError("BoundingBox requires min < max for lon and lat.")

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return ``(min_lon, min_lat, max_lon, max_lat)``."""

        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


@dataclass(frozen=True, slots=True)
class OsmRoad:
    """A road centreline extracted from OSM, with geodesic length in metres."""

    osm_id: int
    highway: str
    length_m: float
    geometry: dict = field(repr=False)


@dataclass(frozen=True, slots=True)
class OsmPark:
    """A park / green-space polygon from OSM, with geodesic area in m²."""

    osm_id: int
    name: str | None
    area_m2: float
    geometry: dict = field(repr=False)


@dataclass(frozen=True, slots=True)
class OsmBuilding:
    """A building footprint from OSM, with geodesic area in m²."""

    osm_id: int
    area_m2: float
    geometry: dict = field(repr=False)


@dataclass(frozen=True, slots=True)
class OsmContext:
    """OSM-derived urban context for one AOI.

    Summary metrics are pre-aggregated so indicator assembly can read
    them without re-traversing feature lists.
    """

    roads: tuple[OsmRoad, ...]
    parks: tuple[OsmPark, ...]
    buildings: tuple[OsmBuilding, ...]
    total_road_length_m: float
    total_park_area_m2: float
    total_building_area_m2: float
    aoi_area_m2: float
    bounding_box: BoundingBox

    @property
    def road_density_m_per_km2(self) -> float:
        """Road length (m) per square kilometre of AOI."""

        area_km2 = self.aoi_area_m2 / 1_000_000.0
        if area_km2 <= 0:
            return 0.0
        return self.total_road_length_m / area_km2

    @property
    def built_up_ratio(self) -> float:
        """Building footprint area as a fraction of AOI area (0–1)."""

        if self.aoi_area_m2 <= 0:
            return 0.0
        return min(self.total_building_area_m2 / self.aoi_area_m2, 1.0)

    @property
    def park_coverage_ratio(self) -> float:
        """Park area as a fraction of AOI area (0–1)."""

        if self.aoi_area_m2 <= 0:
            return 0.0
        return min(self.total_park_area_m2 / self.aoi_area_m2, 1.0)
