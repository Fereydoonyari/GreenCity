"""Unit tests for indicator weights and scoring profile entities."""

import pytest

from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.indicator_weights import IndicatorWeights
from uuid import uuid4


def test_balanced_default_sums_to_one() -> None:
    weights = IndicatorWeights.balanced_default()
    assert abs(sum(weights.as_dict().values()) - 1.0) < 1e-9
    assert weights.vegetation_coverage == pytest.approx(0.25)


def test_weights_reject_bad_sum() -> None:
    with pytest.raises(ValidationError):
        IndicatorWeights(
            vegetation_coverage=0.5,
            green_area_per_m2=0.5,
            road_density=0.5,
            built_up_ratio=0.0,
        )


def test_weights_reject_unknown_key() -> None:
    with pytest.raises(ValidationError):
        IndicatorWeights.from_mapping(
            {
                **IndicatorWeights.balanced_default().as_dict(),
                "unknown": 0.1,
            }
        )


def test_legacy_weights_migrate() -> None:
    migrated = IndicatorWeights.from_mapping(
        {
            "vegetation_coverage": 0.20,
            "green_area_per_capita": 0.20,
            "park_accessibility": 0.20,
            "road_density": 0.15,
            "built_up_ratio": 0.15,
            "population_density": 0.10,
        }
    )
    assert abs(sum(migrated.as_dict().values()) - 1.0) < 1e-9
    assert "park_accessibility" not in migrated.as_dict()
    assert "population_density" not in migrated.as_dict()
    assert "green_area_per_capita" not in migrated.as_dict()
    assert "green_area_per_m2" in migrated.as_dict()


def test_scoring_profile_factory() -> None:
    profile = ScoringProfile.create_balanced_default(owner_id=uuid4())
    assert profile.is_default is True
    assert profile.weights.vegetation_coverage == pytest.approx(0.25)
