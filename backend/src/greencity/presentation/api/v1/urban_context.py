"""HTTP endpoints for OSM urban context."""

from __future__ import annotations

import math
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from shapely.geometry import mapping, shape

from greencity.application.use_cases.urban_context import (
    FetchOsmContextCommand,
    FetchOsmContextUseCase,
)
from greencity.domain.exceptions import NotFoundError
from greencity.domain.value_objects.urban_context import OsmContext
from greencity.presentation.dependencies import (
    UnitOfWorkDep,
    provide_fetch_osm_context_use_case,
)
from greencity.presentation.schemas.urban_context import (
    BoundingBoxSchema,
    OsmBuildingSummary,
    OsmContextResponse,
    OsmParkSummary,
    OsmRoadSummary,
    ParksLayerResponse,
)

router = APIRouter(prefix="/urban-context", tags=["urban-context"])

# Match park catchment used by OSM parser / accessibility (~800 m).
_PARK_CATCHMENT_M = 800.0


def _osm_to_response(ctx: OsmContext, *, max_features: int = 50) -> OsmContextResponse:
    return OsmContextResponse(
        total_road_length_m=ctx.total_road_length_m,
        total_park_area_m2=ctx.total_park_area_m2,
        total_building_area_m2=ctx.total_building_area_m2,
        aoi_area_m2=ctx.aoi_area_m2,
        road_density_m_per_km2=ctx.road_density_m_per_km2,
        built_up_ratio=ctx.built_up_ratio,
        park_coverage_ratio=ctx.park_coverage_ratio,
        road_count=len(ctx.roads),
        park_count=len(ctx.parks),
        building_count=len(ctx.buildings),
        bounding_box=BoundingBoxSchema(
            min_lon=ctx.bounding_box.min_lon,
            min_lat=ctx.bounding_box.min_lat,
            max_lon=ctx.bounding_box.max_lon,
            max_lat=ctx.bounding_box.max_lat,
        ),
        roads=[
            OsmRoadSummary(osm_id=r.osm_id, highway=r.highway, length_m=r.length_m)
            for r in ctx.roads[:max_features]
        ],
        parks=[
            OsmParkSummary(osm_id=p.osm_id, name=p.name, area_m2=p.area_m2)
            for p in ctx.parks[:max_features]
        ],
        buildings=[
            OsmBuildingSummary(osm_id=b.osm_id, area_m2=b.area_m2)
            for b in ctx.buildings[:max_features]
        ],
    )


def _parks_layer_response(aoi_geojson: dict[str, Any], ctx: OsmContext) -> ParksLayerResponse:
    """Build a parks FeatureCollection tagged inside vs nearby the AOI."""

    aoi = shape(aoi_geojson)
    minx, miny, maxx, maxy = aoi.bounds
    mean_lat = (miny + maxy) / 2.0
    lat_pad = _PARK_CATCHMENT_M / 111_320.0
    lon_pad = _PARK_CATCHMENT_M / max(111_320.0 * math.cos(math.radians(mean_lat)), 1.0)
    catchment = aoi.buffer(min(lat_pad, lon_pad))

    features: list[dict[str, Any]] = []
    inside_n = nearby_n = 0
    for park in ctx.parks:
        try:
            geom = shape(park.geometry)
        except Exception:  # noqa: BLE001
            continue
        if geom.is_empty or not geom.intersects(catchment):
            continue
        location = "inside" if aoi.intersects(geom) else "nearby"
        if location == "inside":
            inside_n += 1
        else:
            nearby_n += 1
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": {
                    "osm_id": park.osm_id,
                    "name": park.name or f"Park {park.osm_id}",
                    "area_m2": round(float(park.area_m2), 1),
                    "location": location,
                    "mask_kind": "park",
                },
            }
        )

    return ParksLayerResponse(
        features=features,
        properties={
            "mask_kind": "parks",
            "catchment_m": _PARK_CATCHMENT_M,
            "inside_count": inside_n,
            "nearby_count": nearby_n,
            "count": len(features),
            "catchment": {
                "type": "Feature",
                "geometry": mapping(catchment),
                "properties": {
                    "mask_kind": "park_catchment",
                    "radius_m": _PARK_CATCHMENT_M,
                },
            },
        },
    )


@router.get(
    "/aois/{aoi_id}/osm",
    response_model=OsmContextResponse,
    summary="Fetch OSM urban context for an AOI",
)
def get_osm_context(
    aoi_id: UUID,
    use_case: Annotated[FetchOsmContextUseCase, Depends(provide_fetch_osm_context_use_case)],
) -> OsmContextResponse:
    """Query Overpass for roads, parks, and buildings intersecting the AOI."""

    ctx = use_case.execute(FetchOsmContextCommand(aoi_id=aoi_id))
    return _osm_to_response(ctx)


@router.get(
    "/aois/{aoi_id}/parks",
    response_model=ParksLayerResponse,
    summary="Fetch OSM parks inside an AOI and within the nearby catchment",
)
def get_parks_layer(
    aoi_id: UUID,
    uow: UnitOfWorkDep,
    use_case: Annotated[FetchOsmContextUseCase, Depends(provide_fetch_osm_context_use_case)],
) -> ParksLayerResponse:
    """Return park polygons for map marking (inside AOI + ~800 m nearby)."""

    aoi = uow.areas_of_interest.get_by_id(aoi_id)
    if aoi is None:
        raise NotFoundError(f"Area of interest '{aoi_id}' was not found.")
    ctx = use_case.execute(FetchOsmContextCommand(aoi_id=aoi_id))
    return _parks_layer_response(aoi.geometry.data, ctx)
