"""Indicator weight value objects for Green Deficiency scoring profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from greencity.domain.exceptions import ValidationError

# Canonical indicator keys used by the ranking engine.
INDICATOR_KEYS: tuple[str, ...] = (
    "vegetation_coverage",
    "green_area_per_m2",
    "road_density",
    "built_up_ratio",
)

# Dropped from GDS, or renamed (value remapped onto the new key).
_LEGACY_REMOVED_KEYS = frozenset(
    {"park_accessibility", "population_density", "green_area_per_capita"}
)
_LEGACY_KEY_ALIASES: dict[str, str] = {
    "green_area_per_capita": "green_area_per_m2",
}
_WEIGHT_SUM_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class IndicatorWeights:
    """Relative weights for green-deficiency indicators.

    Weights must be non-negative and sum to ``1.0`` (within floating-point tolerance).
    Directionality (whether a high value increases deficiency) is applied later by
    the scoring engine; profiles only store relative importance.
    """

    vegetation_coverage: float
    green_area_per_m2: float
    road_density: float
    built_up_ratio: float

    def __post_init__(self) -> None:
        values = self.as_dict()
        for key, value in values.items():
            if value < 0:
                raise ValidationError(f"Weight '{key}' must be non-negative.")
        total = sum(values.values())
        if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
            raise ValidationError(
                f"Indicator weights must sum to 1.0 (received {total:.6f})."
            )

    def as_dict(self) -> dict[str, float]:
        """Return weights keyed by canonical indicator name."""

        return {
            "vegetation_coverage": self.vegetation_coverage,
            "green_area_per_m2": self.green_area_per_m2,
            "road_density": self.road_density,
            "built_up_ratio": self.built_up_ratio,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, float]) -> IndicatorWeights:
        """Build weights from a mapping of canonical keys.

        Legacy profiles may still include removed keys or the old
        ``green_area_per_capita`` name; those are migrated automatically.
        """

        normalised_input: dict[str, float] = {}
        for key, value in mapping.items():
            canonical = _LEGACY_KEY_ALIASES.get(key, key)
            if canonical in INDICATOR_KEYS:
                # Prefer an explicit modern key over a legacy alias.
                if canonical in normalised_input and key in _LEGACY_KEY_ALIASES:
                    continue
                normalised_input[canonical] = float(value)

        extras = [
            key
            for key in mapping
            if key not in INDICATOR_KEYS
            and key not in _LEGACY_REMOVED_KEYS
            and key not in _LEGACY_KEY_ALIASES
        ]
        if extras:
            raise ValidationError(
                "Unknown indicator weight(s): " + ", ".join(sorted(extras))
            )

        legacy_present = any(key in mapping for key in _LEGACY_REMOVED_KEYS)
        known = {key: normalised_input[key] for key in INDICATOR_KEYS if key in normalised_input}

        if legacy_present:
            if not known:
                return cls.balanced_default()
            total = sum(known.get(key, 0.0) for key in INDICATOR_KEYS)
            if total <= 0:
                return cls.balanced_default()
            return cls(**{key: known.get(key, 0.0) / total for key in INDICATOR_KEYS})

        missing = [key for key in INDICATOR_KEYS if key not in known]
        if missing:
            raise ValidationError("Missing indicator weight(s): " + ", ".join(missing))
        return cls(**{key: known[key] for key in INDICATOR_KEYS})

    @classmethod
    def balanced_default(cls) -> IndicatorWeights:
        """Return equal weights across the four scored indicators."""

        return cls(
            vegetation_coverage=0.25,
            green_area_per_m2=0.25,
            road_density=0.25,
            built_up_ratio=0.25,
        )
