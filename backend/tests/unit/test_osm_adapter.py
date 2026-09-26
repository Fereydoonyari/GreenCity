"""Unit tests for OverpassOsmAdapter with a stub HTTP client."""

from __future__ import annotations

import urllib.error

from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import BoundingBox
from greencity.infrastructure.osm.adapter import OverpassOsmAdapter
from greencity.infrastructure.osm.query import build_urban_context_query


SAMPLE = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.35, 48.85],
            [2.36, 48.85],
            [2.36, 48.86],
            [2.35, 48.86],
            [2.35, 48.85],
        ]
    ],
}


def test_build_query_contains_bbox_and_filters() -> None:
    bbox = BoundingBox(min_lon=2.35, min_lat=48.85, max_lon=2.36, max_lat=48.86)
    query = build_urban_context_query(bbox)
    assert "highway" in query
    assert "landuse" in query
    assert 'leisure"~"^(park|garden|nature_reserve|recreation_ground)$"' in query
    assert "48.85,2.35,48.86,2.36" in query
    # Main query stays light — footprints are a separate request.
    assert 'way["building"]' not in query


def test_small_bbox_requests_buildings_separately() -> None:
    from greencity.infrastructure.osm.query import should_include_buildings

    bbox = BoundingBox(min_lon=2.35, min_lat=48.85, max_lon=2.36, max_lat=48.86)
    assert should_include_buildings(bbox) is True


def test_adapter_uses_injected_http() -> None:
    called: list[str] = []

    def fake_http(url: str, query: str) -> dict:
        called.append(query)
        if "building" in query and "highway" not in query:
            return {
                "elements": [
                    {
                        "type": "way",
                        "id": 9,
                        "tags": {"building": "yes"},
                        "geometry": [
                            {"lat": 48.855, "lon": 2.353},
                            {"lat": 48.855, "lon": 2.354},
                            {"lat": 48.856, "lon": 2.354},
                            {"lat": 48.856, "lon": 2.353},
                            {"lat": 48.855, "lon": 2.353},
                        ],
                    }
                ]
            }
        return {
            "elements": [
                {
                    "type": "way",
                    "id": 1,
                    "tags": {"highway": "residential"},
                    "geometry": [
                        {"lat": 48.851, "lon": 2.351},
                        {"lat": 48.851, "lon": 2.355},
                    ],
                },
                {
                    "type": "way",
                    "id": 2,
                    "tags": {"landuse": "residential"},
                    "geometry": [
                        {"lat": 48.852, "lon": 2.352},
                        {"lat": 48.852, "lon": 2.354},
                        {"lat": 48.854, "lon": 2.354},
                        {"lat": 48.854, "lon": 2.352},
                        {"lat": 48.852, "lon": 2.352},
                    ],
                },
            ]
        }

    adapter = OverpassOsmAdapter(http_post=fake_http, cache_ttl_s=0)
    ctx = adapter.fetch(GeoJsonGeometry(data=SAMPLE))
    assert any("highway" in q for q in called)
    assert any('way["building"]' in q for q in called)
    assert len(ctx.roads) == 1
    assert ctx.total_road_length_m > 0
    assert ctx.built_up_ratio > 0


def test_adapter_ignores_footways() -> None:
    def fake_http(_url: str, query: str) -> dict:
        if "building" in query and "highway" not in query:
            return {"elements": []}
        return {
            "elements": [
                {
                    "type": "way",
                    "id": 1,
                    "tags": {"highway": "footway"},
                    "geometry": [
                        {"lat": 48.851, "lon": 2.351},
                        {"lat": 48.851, "lon": 2.355},
                    ],
                },
                {
                    "type": "way",
                    "id": 2,
                    "tags": {"highway": "primary"},
                    "geometry": [
                        {"lat": 48.852, "lon": 2.351},
                        {"lat": 48.852, "lon": 2.355},
                    ],
                },
            ]
        }

    adapter = OverpassOsmAdapter(http_post=fake_http, cache_ttl_s=0)
    ctx = adapter.fetch(GeoJsonGeometry(data=SAMPLE))
    assert len(ctx.roads) == 1
    assert ctx.roads[0].highway == "primary"


def test_adapter_empty_response() -> None:
    adapter = OverpassOsmAdapter(http_post=lambda _u, _q: {"elements": []}, cache_ttl_s=0)
    ctx = adapter.fetch(GeoJsonGeometry(data=SAMPLE))
    assert ctx.roads == ()
    assert ctx.aoi_area_m2 > 0


def test_parallel_http_skips_empty_winner(monkeypatch) -> None:
    """Empty regional responses must not beat a slower full payload."""

    from greencity.infrastructure.osm import adapter as osm_adapter

    class _FakeResponse:
        def __init__(self, body: bytes):
            self._body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return self._body

    def fake_urlopen(request, timeout=40):  # noqa: ANN001
        url = request.full_url
        if "osm.ch" in url:
            return _FakeResponse(b'{"elements":[]}')
        return _FakeResponse(
            b'{"elements":[{"type":"way","id":1,"tags":{"highway":"residential"},'
            b'"geometry":[{"lat":48.85,"lon":2.35},{"lat":48.85,"lon":2.36}]}]}'
        )

    monkeypatch.setattr(osm_adapter.urllib.request, "urlopen", fake_urlopen)
    post = osm_adapter._make_http_post(
        mirror_urls=("https://overpass.osm.ch/api/interpreter",),
        timeout_s=5.0,
        retries_per_mirror=1,
        primary_url="https://overpass-api.de/api/interpreter",
    )
    payload = post("https://overpass-api.de/api/interpreter", "[out:json];out;")
    assert len(payload["elements"]) == 1


def test_default_http_retries_on_timeout(monkeypatch) -> None:
    from greencity.infrastructure.osm import adapter as osm_adapter

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return b'{"elements":[{"type":"way","id":1}]}'

    def fake_urlopen(request, timeout=40):  # noqa: ANN001
        if "overpass-api.de" in request.full_url:
            raise TimeoutError("The read operation timed out")
        return _FakeResponse()

    monkeypatch.setattr(osm_adapter.urllib.request, "urlopen", fake_urlopen)
    payload = osm_adapter._default_http_post(
        "https://overpass-api.de/api/interpreter",
        "[out:json];out;",
    )
    assert payload["elements"]


def test_default_http_retries_on_http_error(monkeypatch) -> None:
    from greencity.infrastructure.osm import adapter as osm_adapter

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return b'{"elements":[{"type":"way","id":1}]}'

    def fake_urlopen(request, timeout=40):  # noqa: ANN001
        url = request.full_url
        if "overpass-api.de" in url:
            raise urllib.error.HTTPError(
                url, 504, "Gateway Timeout", hdrs=None, fp=None  # type: ignore[arg-type]
            )
        return _FakeResponse()

    monkeypatch.setattr(osm_adapter.urllib.request, "urlopen", fake_urlopen)
    payload = osm_adapter._default_http_post(
        "https://overpass-api.de/api/interpreter",
        "[out:json];out;",
    )
    assert payload["elements"]


def test_adapter_soft_fails_to_empty_context() -> None:
    def boom(_url: str, _query: str) -> dict:
        raise TimeoutError("timed out")

    adapter = OverpassOsmAdapter(http_post=boom, soft_fail=True, cache_ttl_s=0)
    ctx = adapter.fetch(GeoJsonGeometry(data=SAMPLE))
    assert ctx.roads == ()
    assert ctx.parks == ()
    assert ctx.aoi_area_m2 > 0


def test_adapter_disk_cache_avoids_second_http(tmp_path) -> None:
    calls = {"n": 0}

    def fake_http(_url: str, _query: str) -> dict:
        calls["n"] += 1
        return {
            "elements": [
                {
                    "type": "way",
                    "id": 1,
                    "tags": {"highway": "residential"},
                    "geometry": [
                        {"lat": 48.851, "lon": 2.351},
                        {"lat": 48.851, "lon": 2.355},
                    ],
                }
            ]
        }

    adapter = OverpassOsmAdapter(
        http_post=fake_http,
        soft_fail=True,
        cache_ttl_s=3_600,
        cache_dir=str(tmp_path / "overpass"),
    )
    geo = GeoJsonGeometry(data=SAMPLE)
    adapter.fetch(geo)
    first = calls["n"]
    assert first >= 1  # main query (+ optional buildings query)
    adapter.fetch(geo)
    assert calls["n"] == first
