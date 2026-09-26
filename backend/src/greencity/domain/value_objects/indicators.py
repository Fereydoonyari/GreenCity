"""Raw environmental / urban-form indicator values.

These are measured quantities for one AOI. The scoring engine normalises and
weights them into a Green Deficiency Score; this module only computes
the inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.indicator_weights import INDICATOR_KEYS


@dataclass(frozen=True, slots=True)
class IndicatorValues:
    """Canonical indicator measurements for a single study area.

    Units:
    - ``vegetation_coverage``: fraction in [0, 1]
    - ``green_area_per_m2``: green area (m²) per AOI area (m²), in [0, 1]
    - ``road_density``: metres of road per km²
    - ``built_up_ratio``: building footprint / AOI area in [0, 1]
    """

    vegetation_coverage: float
    green_area_per_m2: float
    road_density: float
    built_up_ratio: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.vegetation_coverage <= 1.0:
            raise ValidationError("vegetation_coverage must be between 0 and 1.")
        if not 0.0 <= self.green_area_per_m2 <= 1.0:
            raise ValidationError("green_area_per_m2 must be between 0 and 1.")
        if self.road_density < 0:
            raise ValidationError("road_density must be non-negative.")
        if not 0.0 <= self.built_up_ratio <= 1.0:
            raise ValidationError("built_up_ratio must be between 0 and 1.")

    def as_dict(self) -> dict[str, float]:
        """Return indicators keyed by canonical name."""

        return {
            "vegetation_coverage": self.vegetation_coverage,
            "green_area_per_m2": self.green_area_per_m2,
            "road_density": self.road_density,
            "built_up_ratio": self.built_up_ratio,
        }

    @classmethod
    def from_mapping(cls, mapping: dict[str, float]) -> IndicatorValues:
        """Build from a mapping of canonical indicator keys."""

        missing = [key for key in INDICATOR_KEYS if key not in mapping]
        if missing:
            raise ValidationError("Missing indicator(s): " + ", ".join(missing))
        return cls(**{key: float(mapping[key]) for key in INDICATOR_KEYS})


def compute_green_area_per_m2(*, green_area_m2: float, aoi_area_m2: float) -> float:
    """Return green area density: m² green per m² of AOI (clamped to [0, 1])."""

    if green_area_m2 < 0:
        raise ValidationError("green_area_m2 must be non-negative.")
    if aoi_area_m2 < 0:
        raise ValidationError("aoi_area_m2 must be non-negative.")
    if aoi_area_m2 <= 0:
        return 0.0
    return max(0.0, min(1.0, green_area_m2 / aoi_area_m2))


def assemble_indicator_values(
    *,
    vegetation_coverage: float,
    green_area_m2: float,
    road_density_m_per_km2: float,
    built_up_ratio: float,
    aoi_area_m2: float,
) -> IndicatorValues:
    """Assemble the scored indicators from measured inputs.

    Pure domain function – no I/O.
    """

    return IndicatorValues(
        vegetation_coverage=max(0.0, min(1.0, vegetation_coverage)),
        green_area_per_m2=compute_green_area_per_m2(
            green_area_m2=max(0.0, green_area_m2),
            aoi_area_m2=max(0.0, aoi_area_m2),
        ),
        road_density=max(0.0, road_density_m_per_km2),
        built_up_ratio=max(0.0, min(1.0, built_up_ratio)),
    )
