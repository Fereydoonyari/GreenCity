"""HTTP endpoints for environmental / accessibility indicator computation."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from greencity.application.use_cases.indicators import (
    ComputeIndicatorsCommand,
    ComputeIndicatorsUseCase,
    IndicatorComputationResult,
)
from greencity.presentation.dependencies import provide_compute_indicators_use_case
from greencity.presentation.schemas.indicators import (
    ComputeIndicatorsRequest,
    IndicatorComputationResponse,
    IndicatorValuesSchema,
)

router = APIRouter(prefix="/indicators", tags=["indicators"])


def _to_response(aoi_id: UUID, result: IndicatorComputationResult) -> IndicatorComputationResponse:
    ind = result.indicators
    return IndicatorComputationResponse(
        aoi_id=aoi_id,
        indicators=IndicatorValuesSchema(
            vegetation_coverage=ind.vegetation_coverage,
            green_area_per_m2=ind.green_area_per_m2,
            road_density=ind.road_density,
            built_up_ratio=ind.built_up_ratio,
        ),
        vegetation_source=result.vegetation_source,
        green_area_source=result.green_area_source,
        aoi_area_m2=result.osm.aoi_area_m2,
        road_count=len(result.osm.roads),
        park_count=len(result.osm.parks),
        building_count=len(result.osm.buildings),
        vegetation_mask=result.vegetation_mask,
        vegetation_hotspot_mask=result.vegetation_hotspot_mask,
        park_access_mask=result.park_access_mask,
        heat_exposure_mask=result.heat_exposure_mask,
        mean_nearest_park_distance_m=result.mean_nearest_park_distance_m,
        median_nearest_park_distance_m=result.median_nearest_park_distance_m,
        mean_nearest_park_walk_min=result.mean_nearest_park_walk_min,
        median_nearest_park_walk_min=result.median_nearest_park_walk_min,
        mean_lst_c=result.mean_lst_c,
        heat_source=result.heat_source,
    )


@router.post(
    "/aois/{aoi_id}/compute",
    response_model=IndicatorComputationResponse,
    summary="Compute environmental and accessibility indicators for an AOI",
)
def compute_indicators(
    aoi_id: UUID,
    body: ComputeIndicatorsRequest,
    use_case: Annotated[ComputeIndicatorsUseCase, Depends(provide_compute_indicators_use_case)],
) -> IndicatorComputationResponse:
    """Fetch OSM context, then assemble the four canonical indicators.

    Optional body fields override vegetation coverage / green area (e.g. from
    the NDVI pipeline). When omitted, OSM park metrics are used as proxies.
    """

    result = use_case.execute(
        ComputeIndicatorsCommand(
            aoi_id=aoi_id,
            vegetation_coverage=body.vegetation_coverage,
            green_area_m2=body.green_area_m2,
            park_walk_distance_m=body.park_walk_distance_m,
        )
    )
    return _to_response(aoi_id, result)
