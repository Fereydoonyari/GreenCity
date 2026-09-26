"""Overpass API implementation of ``OsmDataPort``."""

from __future__ import annotations

import json
import logging
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Sequence

from shapely.geometry.base import BaseGeometry

from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import BoundingBox, OsmContext
from greencity.infrastructure.gis import area_m2, bounding_box_of, geojson_to_shapely
from greencity.infrastructure.osm.cache import OverpassDiskCache
from greencity.infrastructure.osm.parser import empty_osm_context, parse_overpass_response
from greencity.infrastructure.osm.query import (
    DEFAULT_OVERPASS_URL,
    OVERPASS_MIRROR_URLS,
    build_buildings_query,
    build_urban_context_query,
    should_include_buildings,
)

_log = logging.getLogger(__name__)

HttpPostJson = Callable[[str, str], dict[str, Any]]

_USER_AGENT = "GreenCityAI/0.1 (urban-green-planning; contact=local-dev)"
_REQUEST_TIMEOUT_S = 40.0


def _post_once(url: str, query: str, *, timeout: float = _REQUEST_TIMEOUT_S) -> dict[str, Any]:
    """POST one Overpass QL query to ``url`` and return the JSON payload."""

    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _candidate_urls(primary: str, mirror_urls: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    for candidate in (primary, *mirror_urls):
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _make_http_post(
    *,
    mirror_urls: Sequence[str],
    timeout_s: float,
    retries_per_mirror: int,
    primary_url: str = DEFAULT_OVERPASS_URL,
) -> HttpPostJson:
    """Race Overpass endpoints in parallel; first non-empty payload wins.

    Empty responses (regional mirrors) do not win the race. If every endpoint
    fails or returns empty, the last empty payload is returned or an error raised.
    """

    def http_post(url: str, query: str) -> dict[str, Any]:
        candidates = _candidate_urls(url or primary_url, mirror_urls)
        if not candidates:
            raise ValidationError("No Overpass endpoints configured.")

        def attempt(candidate: str) -> dict[str, Any]:
            last_error: Exception | None = None
            for try_idx in range(max(1, retries_per_mirror)):
                try:
                    _log.info("Querying Overpass at %s (attempt %s)", candidate, try_idx + 1)
                    return _post_once(candidate, query, timeout=timeout_s)
                except urllib.error.HTTPError as exc:
                    try:
                        err_body = exc.read().decode("utf-8", errors="replace")
                    except Exception:  # noqa: BLE001
                        err_body = getattr(exc, "reason", "") or ""
                    last_error = ValidationError(
                        f"Overpass API error {exc.code}: {str(err_body)[:200]}"
                    )
                except (TimeoutError, socket.timeout) as exc:
                    last_error = ValidationError(f"Overpass API timeout: {exc}")
                except urllib.error.URLError as exc:
                    reason = exc.reason
                    if isinstance(reason, (TimeoutError, socket.timeout)):
                        last_error = ValidationError(f"Overpass API timeout: {reason}")
                    else:
                        last_error = ValidationError(f"Overpass API unreachable: {reason}")
                except OSError as exc:
                    last_error = ValidationError(f"Overpass API network error: {exc}")
                if try_idx + 1 < retries_per_mirror:
                    time.sleep(0.4 * (2**try_idx))
            assert last_error is not None
            raise last_error

        empty_payload: dict[str, Any] | None = None
        errors: list[Exception] = []

        with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
            futures = {pool.submit(attempt, candidate): candidate for candidate in candidates}
            for future in as_completed(futures):
                candidate = futures[future]
                try:
                    payload = future.result()
                except Exception as exc:  # noqa: BLE001
                    _log.warning("Overpass %s failed (%s)", candidate, exc)
                    errors.append(exc if isinstance(exc, Exception) else ValidationError(str(exc)))
                    continue
                elements = payload.get("elements") or []
                if elements:
                    _log.info(
                        "Overpass %s returned %s elements",
                        candidate,
                        len(elements),
                    )
                    return payload
                _log.warning("Overpass %s returned 0 elements; waiting for other endpoints", candidate)
                empty_payload = payload

        if empty_payload is not None:
            return empty_payload
        if errors:
            raise errors[-1]
        raise ValidationError("Overpass returned no data.")

    return http_post


def _default_http_post(url: str, query: str) -> dict[str, Any]:
    return _make_http_post(
        mirror_urls=OVERPASS_MIRROR_URLS,
        timeout_s=_REQUEST_TIMEOUT_S,
        retries_per_mirror=1,
        primary_url=url,
    )(url, query)


class OverpassOsmAdapter:
    """Fetch roads, parks, and built fabric via the Overpass API.

    Uses one Overpass query: highways + parks + built landuse, and building
    footprints for neighborhood-sized AOIs. Soft-fails to an empty context.
    """

    def __init__(
        self,
        *,
        overpass_url: str = DEFAULT_OVERPASS_URL,
        http_post: HttpPostJson | None = None,
        soft_fail: bool = True,
        mirror_urls: Sequence[str] | None = None,
        timeout_s: float = _REQUEST_TIMEOUT_S,
        retries_per_mirror: int = 1,
        cache_ttl_s: int = 0,
        cache_dir: str = ".cache/overpass",
    ) -> None:
        self._url = overpass_url
        mirrors = tuple(mirror_urls) if mirror_urls is not None else OVERPASS_MIRROR_URLS
        self._http_post = http_post or _make_http_post(
            mirror_urls=mirrors,
            timeout_s=timeout_s,
            retries_per_mirror=retries_per_mirror,
            primary_url=overpass_url,
        )
        self._soft_fail = soft_fail
        self._cache = OverpassDiskCache(cache_dir, ttl_s=cache_ttl_s)

    def _fetch_payload(self, query: str) -> dict[str, Any] | None:
        cached = self._cache.get(query)
        if cached is not None and cached.get("elements"):
            return cached
        try:
            payload = self._http_post(self._url, query)
            if payload.get("elements"):
                self._cache.set(query, payload)
            return payload
        except (ValidationError, TimeoutError, OSError) as exc:
            if not self._soft_fail:
                raise
            _log.warning("Overpass query failed (%s)", exc)
            return None

    def fetch(self, geometry: GeoJsonGeometry) -> OsmContext:
        """Query Overpass for the AOI and clip features to the AOI polygon."""

        aoi = geojson_to_shapely(geometry)
        if aoi.is_empty:
            raise ValidationError("AOI geometry is empty.")
        bbox = bounding_box_of(aoi)
        aoi_area = area_m2(aoi)
        query = build_urban_context_query(bbox)
        _log.info("Querying Overpass for bbox %s", bbox.as_tuple())

        payload = self._fetch_payload(query)
        if not payload or not payload.get("elements"):
            _log.warning("Overpass returned no elements for bbox %s", bbox.as_tuple())
            return empty_osm_context(aoi_area=aoi_area, bbox=bbox)

        # Neighborhood-sized AOIs: add building footprints in a second query so a
        # building timeout cannot wipe roads/landuse from the main response.
        if should_include_buildings(bbox):
            _log.info("Fetching building footprints for small AOI %s", bbox.as_tuple())
            buildings_payload = self._fetch_payload(build_buildings_query(bbox))
            if buildings_payload and buildings_payload.get("elements"):
                seen: set[tuple[str, int]] = set()
                merged: list[Any] = []
                for element in list(payload.get("elements") or []) + list(
                    buildings_payload.get("elements") or []
                ):
                    key = (str(element.get("type", "")), int(element.get("id", 0)))
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(element)
                payload = {"elements": merged}

        ctx = self._parse(payload, aoi=aoi, aoi_area=aoi_area, bbox=bbox)
        _log.info(
            "OSM context: roads=%s (%.0f m, density=%.0f), built_up=%.3f (%s polys), parks=%s",
            len(ctx.roads),
            ctx.total_road_length_m,
            ctx.road_density_m_per_km2,
            ctx.built_up_ratio,
            len(ctx.buildings),
            len(ctx.parks),
        )
        return ctx

    def _parse(
        self,
        payload: dict[str, Any],
        *,
        aoi: BaseGeometry,
        aoi_area: float,
        bbox: BoundingBox,
    ) -> OsmContext:
        return parse_overpass_response(payload, aoi=aoi, aoi_area=aoi_area, bbox=bbox)
