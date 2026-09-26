"""Unit tests for Landsat ST Planetary Computer helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from greencity.infrastructure.imagery import landsat as landsat_mod


SAMPLE_ITEM = {
    "id": "LC09_L2SP_199026_20260629_02_T1",
    "properties": {
        "datetime": "2026-06-29T10:40:00Z",
        "eo:cloud_cover": 12.5,
    },
    "assets": {
        "lwir11": {
            "href": (
                "https://landsateuwest.blob.core.windows.net/landsat-c2/level-2/"
                "standard/oli-tirs/example_ST_B10.TIF"
            ),
            "roles": ["data"],
        }
    },
}


def test_stac_search_parses_features() -> None:
    payload = json.dumps({"features": [SAMPLE_ITEM]}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False

    with patch.object(landsat_mod.urllib.request, "urlopen", return_value=mock_resp):
        features = landsat_mod._stac_search(
            bbox=(2.33, 48.84, 2.38, 48.87),
            start=datetime(2025, 1, 1, tzinfo=UTC),
            end=datetime(2026, 7, 31, tzinfo=UTC),
            max_cloud_cover=60.0,
            limit=5,
        )
    assert len(features) == 1
    assert features[0]["id"] == SAMPLE_ITEM["id"]


def test_band_href_prefers_lwir11() -> None:
    adapter = landsat_mod.LandsatThermalAdapter.__new__(landsat_mod.LandsatThermalAdapter)
    href = adapter._band_href(SAMPLE_ITEM)
    assert "ST_B10" in href.upper()


def test_item_cloud_cover() -> None:
    assert landsat_mod._item_cloud_cover(SAMPLE_ITEM) == pytest.approx(12.5)
    assert landsat_mod._item_cloud_cover({"properties": {}}) == pytest.approx(100.0)


def test_sign_href_reads_signed_url() -> None:
    payload = json.dumps({"href": "https://example.com/signed.tif?sig=1"}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    with patch.object(landsat_mod.urllib.request, "urlopen", return_value=mock_resp):
        signed = landsat_mod._sign_href("https://example.com/raw.tif")
    assert "sig=1" in signed


def test_sign_href_retries_then_token_fallback() -> None:
    token_payload = json.dumps({"token": "sv=1&sig=abc"}).encode("utf-8")
    token_resp = MagicMock()
    token_resp.read.return_value = token_payload
    token_resp.__enter__.return_value = token_resp
    token_resp.__exit__.return_value = False

    with (
        patch.object(
            landsat_mod,
            "_sign_href_once",
            side_effect=ConnectionError("Remote end closed connection"),
        ),
        patch.object(landsat_mod.time, "sleep"),
        patch.object(landsat_mod.urllib.request, "urlopen", return_value=token_resp),
    ):
        signed = landsat_mod._sign_href("https://example.com/raw.tif")
    assert signed.endswith("?sv=1&sig=abc")


def test_live_pc_search_paris_finds_scenes() -> None:
    """Integration smoke: Planetary Computer must return Paris Landsat L2 scenes."""

    features = landsat_mod._stac_search(
        bbox=(2.33, 48.84, 2.38, 48.87),
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2026, 7, 31, tzinfo=UTC),
        max_cloud_cover=60.0,
        limit=5,
    )
    assert features, "Planetary Computer returned no landsat-c2-l2 scenes for Paris"
    assert any(landsat_mod._band_href_from_item(f) for f in features)
