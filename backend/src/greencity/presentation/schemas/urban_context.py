"""Pydantic schemas for OSM urban-context endpoints."""

from pydantic import BaseModel, Field


class OsmRoadSummary(BaseModel):
    """Summary of a single OSM road segment."""

    osm_id: int
    highway: str
    length_m: float


class OsmParkSummary(BaseModel):
    """Summary of a single OSM park polygon."""

    osm_id: int
    name: str | None
    area_m2: float
    geometry: dict | None = Field(
        default=None,
        description="GeoJSON geometry when included (parks layer endpoint).",
    )
    location: str | None = Field(
        default=None,
        description="'inside' the AOI or 'nearby' within the walk catchment.",
    )


class ParksLayerResponse(BaseModel):
    """GeoJSON FeatureCollection of parks inside / near an AOI."""

    type: str = "FeatureCollection"
    features: list[dict] = Field(default_factory=list)
    properties: dict = Field(default_factory=dict)


class OsmBuildingSummary(BaseModel):
    """Summary of a single OSM building footprint."""

    osm_id: int
    area_m2: float


class BoundingBoxSchema(BaseModel):
    """WGS84 bounding box."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


class OsmContextResponse(BaseModel):
    """OSM urban context for an AOI (feature lists truncated for HTTP payloads)."""

    total_road_length_m: float
    total_park_area_m2: float
    total_building_area_m2: float
    aoi_area_m2: float
    road_density_m_per_km2: float
    built_up_ratio: float
    park_coverage_ratio: float
    road_count: int
    park_count: int
    building_count: int
    bounding_box: BoundingBoxSchema
    roads: list[OsmRoadSummary] = Field(default_factory=list)
    parks: list[OsmParkSummary] = Field(default_factory=list)
    buildings: list[OsmBuildingSummary] = Field(default_factory=list)
