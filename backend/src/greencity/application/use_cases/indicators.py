"""Use case: compute the four canonical indicators for an AOI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.ports.imagery import ImageryAcquisitionPort
from greencity.domain.ports.indicators import ParkAccessibilityPort
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.ports.thermal import ThermalAcquisitionPort
from greencity.domain.ports.urban_context import OsmDataPort
from greencity.domain.ports.vegetation import VegetationPipelinePort
from greencity.domain.value_objects.indicators import IndicatorValues, assemble_indicator_values
from greencity.domain.value_objects.urban_context import OsmContext
from greencity.infrastructure.imagery.hotspot_masks import build_heat_exposure_mask
from greencity.infrastructure.indicators.park_accessibility import build_park_access_mask

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComputeIndicatorsCommand:
    """Input for indicator computation.

    Vegetation inputs are optional. When omitted, HLS NDVI is preferred when
    an imagery port is configured; otherwise OSM park coverage is used as a
    vegetation proxy and park area as green area.
    """

    aoi_id: UUID
    vegetation_coverage: float | None = None
    green_area_m2: float | None = None
    park_walk_distance_m: float = 300.0
    ndvi_threshold: float = 0.2


@dataclass(frozen=True)
class IndicatorComputationResult:
    """Indicators plus the urban-context inputs used to derive them."""

    indicators: IndicatorValues
    osm: OsmContext
    vegetation_source: str
    green_area_source: str
    vegetation_mask: dict | None = None
    vegetation_hotspot_mask: dict | None = None
    park_access_mask: dict | None = None
    heat_exposure_mask: dict | None = None
    mean_nearest_park_distance_m: float | None = None
    median_nearest_park_distance_m: float | None = None
    mean_nearest_park_walk_min: float | None = None
    median_nearest_park_walk_min: float | None = None
    mean_lst_c: float | None = None
    heat_source: str = ""


class ComputeIndicatorsUseCase:
    """Fetch OSM for an AOI and assemble indicator values.

    Optional HLS imagery + NDVI pipeline supply vegetation coverage when
    no manual override is provided. Failures fall back to OSM park proxies.
    Optional Landsat ST supplies a heat-exposure overlay (not scored).
    """

    def __init__(
        self,
        uow: UnitOfWork,
        osm: OsmDataPort,
        park_accessibility: ParkAccessibilityPort,
        imagery: ImageryAcquisitionPort | None = None,
        vegetation_pipeline: VegetationPipelinePort | None = None,
        thermal: ThermalAcquisitionPort | None = None,
    ) -> None:
        self._uow = uow
        self._osm = osm
        self._park_accessibility = park_accessibility
        self._imagery = imagery
        self._vegetation_pipeline = vegetation_pipeline
        self._thermal = thermal

    def execute(self, command: ComputeIndicatorsCommand) -> IndicatorComputationResult:
        """Compute indicators for ``command.aoi_id``."""

        if command.park_walk_distance_m <= 0:
            raise ValidationError("park_walk_distance_m must be positive.")
        if command.vegetation_coverage is not None and not (
            0.0 <= command.vegetation_coverage <= 1.0
        ):
            raise ValidationError("vegetation_coverage must be between 0 and 1.")
        if command.green_area_m2 is not None and command.green_area_m2 < 0:
            raise ValidationError("green_area_m2 must be non-negative.")

        aoi = self._uow.areas_of_interest.get_by_id(command.aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{command.aoi_id}' was not found.")

        osm = self._osm.fetch(aoi.geometry)

        mean_nearest_park: float | None = None
        median_nearest_park: float | None = None
        mean_park_walk_min: float | None = None
        median_park_walk_min: float | None = None
        if hasattr(self._park_accessibility, "compute_metrics"):
            metrics = self._park_accessibility.compute_metrics(
                aoi.geometry,
                osm,
                walk_distance_m=command.park_walk_distance_m,
            )
            if metrics.park_count > 0:
                mean_nearest_park = _finite_or_none(metrics.mean_nearest_park_distance_m)
                median_nearest_park = _finite_or_none(
                    metrics.median_nearest_park_distance_m
                )
                mean_park_walk_min = _finite_or_none(metrics.mean_nearest_park_walk_min)
                median_park_walk_min = _finite_or_none(
                    metrics.median_nearest_park_walk_min
                )

        park_access_mask = build_park_access_mask(
            aoi.geometry,
            osm,
            walk_distance_m=command.park_walk_distance_m,
        )

        vegetation_coverage = command.vegetation_coverage
        vegetation_source = "provided" if vegetation_coverage is not None else ""
        green_area_m2 = command.green_area_m2
        green_area_source = "provided" if green_area_m2 is not None else ""
        vegetation_mask: dict | None = None
        vegetation_hotspot_mask: dict | None = None

        if vegetation_coverage is None and self._imagery is not None and self._vegetation_pipeline is not None:
            try:
                scene = self._imagery.acquire_red_nir(aoi.geometry)
                result = self._vegetation_pipeline.run(
                    red_band=scene.red_band,
                    nir_band=scene.nir_band,
                    nodata_mask=scene.nodata_mask,
                    ndvi_threshold=command.ndvi_threshold,
                    pixel_size_m=scene.pixel_size_m,
                    transform=scene.transform,
                    crs=scene.crs,
                    clip_geojson=aoi.geometry.data,
                )
                vegetation_coverage = result.coverage.vegetated_fraction
                granule = scene.granule_id or "unknown"
                vegetation_source = f"hls_ndvi:{granule}"
                vegetation_mask = result.density_mask
                vegetation_hotspot_mask = result.vegetation_hotspot_mask
                if green_area_m2 is None and result.coverage.green_area_m2 is not None:
                    green_area_m2 = result.coverage.green_area_m2
                    green_area_source = "hls_ndvi"
                _log.info(
                    "AOI %s vegetation from HLS NDVI (%.1f%%, granule=%s, mask_features=%s)",
                    aoi.id,
                    vegetation_coverage * 100,
                    granule,
                    len((vegetation_mask or {}).get("features") or []),
                )
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "HLS vegetation acquisition failed for AOI %s; using OSM proxy (%s)",
                    aoi.id,
                    exc,
                )

        if vegetation_coverage is None:
            vegetation_coverage = osm.park_coverage_ratio
            vegetation_source = "osm_park_coverage_proxy"

        if green_area_m2 is None:
            green_area_m2 = osm.total_park_area_m2
            green_area_source = "osm_park_area"

        heat_exposure_mask: dict | None = None
        mean_lst_c: float | None = None
        heat_source = ""
        if self._thermal is not None:
            try:
                thermal = self._thermal.acquire_thermal(aoi.geometry)
                heat_exposure_mask = build_heat_exposure_mask(
                    thermal.temperature_k,
                    thermal.nodata_mask
                    if thermal.nodata_mask is not None
                    else (thermal.temperature_k != thermal.temperature_k),
                    transform=thermal.transform,
                    crs=thermal.crs,
                    clip_geojson=aoi.geometry.data,
                )
                mean_lst_c = thermal.mean_temperature_c
                granule = thermal.granule_id or "unknown"
                heat_source = f"landsat_st:{granule}"
                _log.info(
                    "AOI %s heat from Landsat ST (mean=%.1f°C, granule=%s, mask_features=%s)",
                    aoi.id,
                    mean_lst_c if mean_lst_c is not None else float("nan"),
                    granule,
                    len((heat_exposure_mask or {}).get("features") or []),
                )
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "Landsat heat acquisition failed for AOI %s; skipping heat overlay (%s)",
                    aoi.id,
                    exc,
                )

        indicators = assemble_indicator_values(
            vegetation_coverage=vegetation_coverage,
            green_area_m2=green_area_m2,
            road_density_m_per_km2=osm.road_density_m_per_km2,
            built_up_ratio=osm.built_up_ratio,
            aoi_area_m2=osm.aoi_area_m2,
        )

        return IndicatorComputationResult(
            indicators=indicators,
            osm=osm,
            vegetation_source=vegetation_source,
            green_area_source=green_area_source,
            vegetation_mask=vegetation_mask,
            vegetation_hotspot_mask=vegetation_hotspot_mask,
            park_access_mask=park_access_mask,
            heat_exposure_mask=heat_exposure_mask,
            mean_nearest_park_distance_m=mean_nearest_park,
            median_nearest_park_distance_m=median_nearest_park,
            mean_nearest_park_walk_min=mean_park_walk_min,
            median_nearest_park_walk_min=median_park_walk_min,
            mean_lst_c=mean_lst_c,
            heat_source=heat_source,
        )


def _finite_or_none(value: float) -> float | None:
    if value != value:  # NaN
        return None
    return float(value)
