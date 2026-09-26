"""Landsat Collection 2 Level-2 surface temperature via Microsoft Planetary Computer.

USGS LandsatLook HTTPS assets require ERS auth that ``earthaccess.open`` does
not satisfy (HTML login pages end up in ``/vsimem/``). Planetary Computer hosts
the same ``ST_B10`` / ``lwir11`` COGs with free SAS-signed HTTPS URLs that
rasterio can window-read without AWS requester-pays.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from shapely.geometry import mapping, shape

from greencity.config import Settings, get_settings
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.imagery import ThermalScene
from greencity.infrastructure.gis import bounding_box_of, geojson_to_shapely

_log = logging.getLogger(__name__)

# Landsat C2 L2 ST_B10: Temperature_K = DN * scale + offset
_ST_SCALE = 0.00341802
_ST_OFFSET = 149.0
_ST_FILL = 0
_ST_VALID_MIN_DN = 293
_PIXEL_SIZE_M = 30.0
_ST_BAND = "ST_B10"
_PRODUCT = "landsat-c2-l2"
_PC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
_PC_SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
_PC_TOKEN = f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{_PRODUCT}"
_STAC_ASSET_KEYS = ("lwir11", "ST_B10", "st_b10")
_HTTP_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "GreenCityAI/0.1 (landsat-st; +https://github.com/)",
}
_SIGN_ATTEMPTS = 4
_SEARCH_ATTEMPTS = 3


class LandsatThermalAdapter:
    """Acquire Landsat C2 L2 surface temperature (ST_B10) for an AOI.

    Searches Planetary Computer STAC for low-cloud ``landsat-c2-l2`` items,
    SAS-signs the ``lwir11`` COG, clips to the AOI, and returns Kelvin arrays.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def acquire_thermal(self, geometry: GeoJsonGeometry) -> ThermalScene:
        """Search Landsat C2 L2 ST and return a clipped scene in Kelvin."""

        aoi = geojson_to_shapely(geometry)
        if aoi.is_empty:
            raise ValidationError("AOI geometry is empty.")

        bbox = bounding_box_of(aoi)
        item = self._search_best_item(bbox.as_tuple())
        st_href = _sign_href(self._band_href(item))
        temperature_k, nodata, transform, crs = self._read_clipped_st(st_href, aoi)

        granule_id = str(item.get("id") or "unknown")
        acquired = _item_datetime(item)

        return ThermalScene(
            temperature_k=temperature_k,
            nodata_mask=nodata,
            pixel_size_m=_PIXEL_SIZE_M,
            source="landsat_st",
            granule_id=granule_id,
            acquired_at=acquired,
            product=_PRODUCT,
            scale_factor=_ST_SCALE,
            additive_offset=_ST_OFFSET,
            fill_value=float(_ST_FILL),
            transform=transform,
            crs=crs,
        )

    def _search_best_item(self, bbox: tuple[float, float, float, float]) -> dict[str, Any]:
        min_lon, min_lat, max_lon, max_lat = bbox
        end = datetime.now(UTC)
        start = end - timedelta(days=self._settings.landsat_lookback_days)
        max_cloud = float(self._settings.landsat_max_cloud_cover)

        _log.info(
            "Searching Planetary Computer %s for bbox=%s temporal=%s..%s cloud<=%s",
            _PRODUCT,
            bbox,
            start.date(),
            end.date(),
            max_cloud,
        )
        features = _stac_search(
            bbox=(min_lon, min_lat, max_lon, max_lat),
            start=start,
            end=end,
            max_cloud_cover=max_cloud,
            limit=25,
        )
        if not features:
            features = _stac_search(
                bbox=(min_lon, min_lat, max_lon, max_lat),
                start=start,
                end=end,
                max_cloud_cover=None,
                limit=25,
            )
            features = [f for f in features if _item_cloud_cover(f) <= max_cloud]

        if not features:
            raise ValidationError(
                f"No {_PRODUCT} scenes found for AOI in the last "
                f"{self._settings.landsat_lookback_days} days "
                f"(cloud ≤ {max_cloud}%)."
            )

        # Prefer items that actually expose a thermal asset.
        with_thermal = [f for f in features if _band_href_from_item(f)]
        pool = with_thermal or features
        ranked = sorted(
            pool,
            key=lambda f: (_item_cloud_cover(f), -_item_timestamp(f)),
        )
        best = ranked[0]
        if not _band_href_from_item(best):
            raise ValidationError(f"Landsat STAC item is missing {_ST_BAND} asset.")
        _log.info(
            "Selected Landsat ST scene cloud=%.1f id=%s",
            _item_cloud_cover(best),
            best.get("id"),
        )
        return best

    def _band_href(self, item: dict[str, Any]) -> str:
        href = _band_href_from_item(item)
        if not href:
            raise ValidationError(f"Landsat STAC item is missing {_ST_BAND} asset.")
        return href

    def _read_clipped_st(
        self,
        st_href: str,
        aoi: Any,
    ) -> tuple[np.ndarray, np.ndarray, tuple[float, ...], str]:
        import rasterio
        from rasterio.mask import mask as rio_mask

        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff",
            GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
            GDAL_HTTP_MAX_RETRY="3",
            GDAL_HTTP_RETRY_DELAY="1",
        ):
            last_exc: Exception | None = None
            for attempt in range(1, 4):
                try:
                    with rasterio.open(st_href) as src:
                        if src.count < 1 or src.width < 2 or src.height < 2:
                            raise ValidationError(
                                "Landsat ST URL did not open as a valid GeoTIFF "
                                "(check network / SAS token)."
                            )
                        aoi_proj = _reproject_aoi_to_crs(aoi, src.crs)
                        image, transform = rio_mask(
                            src,
                            [mapping(aoi_proj)],
                            crop=True,
                            filled=True,
                            nodata=_ST_FILL,
                        )
                        raw = image[0]
                        crs = src.crs
                        crs_str = crs.to_string() if crs else "EPSG:4326"
                    break
                except ValidationError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    delay = min(6.0, 0.5 * (2 ** (attempt - 1)))
                    _log.warning(
                        "Landsat ST COG read attempt %s/3 failed (%s); retrying in %.1fs",
                        attempt,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
            else:
                raise ValidationError(
                    f"Landsat ST COG read failed after retries: {last_exc}"
                ) from last_exc

        nodata = (raw == _ST_FILL) | (raw < _ST_VALID_MIN_DN)
        temperature_k = raw.astype(np.float64) * _ST_SCALE + _ST_OFFSET
        temperature_k[nodata] = np.nan

        if int((~nodata).sum()) == 0:
            raise ValidationError("Landsat ST clip produced no valid pixels inside the AOI.")

        t = transform
        transform_tuple = (
            float(t.a),
            float(t.b),
            float(t.c),
            float(t.d),
            float(t.e),
            float(t.f),
        )
        return temperature_k, nodata, transform_tuple, crs_str


def _band_href_from_item(item: dict[str, Any]) -> str | None:
    assets = item.get("assets") or {}
    for key in _STAC_ASSET_KEYS:
        asset = assets.get(key)
        if isinstance(asset, dict) and asset.get("href"):
            return str(asset["href"])
    for asset in assets.values():
        if not isinstance(asset, dict):
            continue
        href = str(asset.get("href") or "")
        if _ST_BAND.upper() in href.upper():
            return href
    return None


def _sign_href(href: str) -> str:
    """Return a time-limited Planetary Computer SAS URL for ``href``.

    Retries transient connection drops and falls back to the collection
    token endpoint when the per-href sign API is unavailable.
    """

    last_exc: Exception | None = None
    for attempt in range(1, _SIGN_ATTEMPTS + 1):
        try:
            return _sign_href_once(href)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            delay = min(8.0, 0.6 * (2 ** (attempt - 1)))
            _log.warning(
                "PC SAS sign attempt %s/%s failed (%s); retrying in %.1fs",
                attempt,
                _SIGN_ATTEMPTS,
                exc,
                delay,
            )
            time.sleep(delay)

    try:
        signed = _sign_href_via_collection_token(href)
        _log.info("PC SAS sign succeeded via collection token fallback")
        return signed
    except Exception as exc:  # noqa: BLE001
        last_exc = exc

    raise ValidationError(f"Planetary Computer SAS sign failed: {last_exc}") from last_exc


def _sign_href_once(href: str) -> str:
    url = f"{_PC_SIGN}?href={urllib.parse.quote(href, safe='')}"
    req = urllib.request.Request(url, headers=_HTTP_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    signed = data.get("href")
    if not signed:
        raise ValidationError("Planetary Computer SAS sign returned no href.")
    return str(signed)


def _sign_href_via_collection_token(href: str) -> str:
    """Append a collection-scoped SAS token to an unsigned blob URL."""

    req = urllib.request.Request(_PC_TOKEN, headers=_HTTP_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("token")
    if not token:
        raise ValidationError("Planetary Computer token endpoint returned no token.")
    sep = "&" if "?" in href else "?"
    return f"{href}{sep}{token}"


def _stac_search(
    *,
    bbox: tuple[float, float, float, float],
    start: datetime,
    end: datetime,
    max_cloud_cover: float | None,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Query Planetary Computer STAC; returns GeoJSON Feature dicts."""

    body: dict[str, Any] = {
        "collections": [_PRODUCT],
        "bbox": list(bbox),
        "datetime": (
            f"{start.strftime('%Y-%m-%dT00:00:00Z')}/"
            f"{end.strftime('%Y-%m-%dT23:59:59Z')}"
        ),
        "limit": limit,
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
    }
    if max_cloud_cover is not None:
        body["query"] = {"eo:cloud_cover": {"lt": max_cloud_cover}}

    payload = json.dumps(body).encode("utf-8")
    last_exc: Exception | None = None
    for attempt in range(1, _SEARCH_ATTEMPTS + 1):
        req = urllib.request.Request(
            _PC_SEARCH,
            data=payload,
            headers={**_HTTP_HEADERS, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            features = data.get("features") or []
            return [f for f in features if isinstance(f, dict)]
        except urllib.error.HTTPError as exc:
            last_exc = ValidationError(
                f"Planetary Computer STAC search failed: HTTP {exc.code}"
            )
            if exc.code < 500 and exc.code != 429:
                raise last_exc from exc
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
        delay = min(8.0, 0.6 * (2 ** (attempt - 1)))
        _log.warning(
            "PC STAC search attempt %s/%s failed (%s); retrying in %.1fs",
            attempt,
            _SEARCH_ATTEMPTS,
            last_exc,
            delay,
        )
        time.sleep(delay)

    raise ValidationError(f"Planetary Computer STAC search failed: {last_exc}") from last_exc


def _item_cloud_cover(item: dict[str, Any]) -> float:
    props = item.get("properties") or {}
    for key in ("eo:cloud_cover", "cloud_cover"):
        raw = props.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return 100.0


def _item_datetime(item: dict[str, Any]) -> datetime | None:
    props = item.get("properties") or {}
    raw = props.get("datetime") or props.get("start_datetime")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _item_timestamp(item: dict[str, Any]) -> float:
    dt = _item_datetime(item)
    return dt.timestamp() if dt is not None else 0.0


def _reproject_aoi_to_crs(aoi: Any, crs: Any) -> Any:
    import rasterio
    from rasterio.warp import transform_geom

    if crs is None:
        return aoi
    crs_obj = rasterio.crs.CRS.from_user_input(crs)
    if crs_obj.to_epsg() == 4326:
        return aoi
    geom = transform_geom("EPSG:4326", crs_obj, mapping(aoi), precision=6)
    return shape(geom)
