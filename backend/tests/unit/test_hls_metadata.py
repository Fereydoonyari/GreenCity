"""Unit tests for HLS metadata helpers (cloud cover / attributes)."""

from __future__ import annotations

from greencity.infrastructure.imagery.hls import _cloud_cover, _umm_additional_attribute


class _FakeGranule(dict):
    """Minimal earthaccess-like granule mapping."""


def test_cloud_cover_from_additional_attributes() -> None:
    granule = _FakeGranule(
        umm={
            "AdditionalAttributes": [
                {"Name": "PRODUCT_URI", "Values": ["x"]},
                {"Name": "CLOUD_COVERAGE", "Values": ["14"]},
            ]
        }
    )
    assert _umm_additional_attribute(granule, "CLOUD_COVERAGE") == "14"
    assert _cloud_cover(granule) == 14.0


def test_cloud_cover_missing_defaults_to_100() -> None:
    granule = _FakeGranule(umm={"AdditionalAttributes": []})
    assert _cloud_cover(granule) == 100.0
