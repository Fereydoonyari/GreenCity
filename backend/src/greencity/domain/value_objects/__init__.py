"""Domain value objects."""

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.indicator_weights import INDICATOR_KEYS, IndicatorWeights
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmBuilding,
    OsmContext,
    OsmPark,
    OsmRoad,
)
from greencity.domain.value_objects.vegetation import (
    BandStatistics,
    VegetationCoverage,
    VegetationResult,
)

__all__ = [
    "BandStatistics",
    "BoundingBox",
    "GeoJsonGeometry",
    "INDICATOR_KEYS",
    "IndicatorValues",
    "IndicatorWeights",
    "OsmBuilding",
    "OsmContext",
    "OsmPark",
    "OsmRoad",
    "VegetationCoverage",
    "VegetationResult",
]
