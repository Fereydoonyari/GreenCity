"""NASA HLS (HLSS30) imagery acquisition via earthaccess + rasterio."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from shapely.geometry import mapping, shape

from greencity.config import Settings, get_settings
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.imagery import RedNirScene
from greencity.infrastructure.gis import bounding_box_of, geojson_to_shapely

_log = logging.getLogger(__name__)

# HLSS30 surface reflectance scale (DN → reflectance).
_HLS_SCALE = 0.0001
_HLS_FILL = -9999
_PIXEL_SIZE_M = 30.0
_RED_BAND = "B04"
_NIR_BAND = "B8A"
_PRODUCT = "HLSS30"


class HlsEarthAccessAdapter:
    """Acquire Red (B04) + NIR (B8A) from NASA HLSS30 for an AOI.

    Searches the last N days for low-cloud granules covering the AOI bbox,
    opens COG bands via earthaccess, clips to the AOI, and returns float
    reflectance arrays for the NDVI pipeline.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def acquire_red_nir(self, geometry: GeoJsonGeometry) -> RedNirScene:
        """Search HLSS30 and return a clipped Red/NIR scene."""

        if not self._settings.earthaccess_configured:
            raise ValidationError(
                "NASA EarthAccess credentials are not configured "
                "(NASA_EARTHACCESS_USERNAME / NASA_EARTHACCESS_PASSWORD)."
            )

        aoi = geojson_to_shapely(geometry)
        if aoi.is_empty:
            raise ValidationError("AOI geometry is empty.")

        bbox = bounding_box_of(aoi)
        granule = self._search_best_granule(bbox.as_tuple())
        red_href, nir_href = self._band_hrefs(granule)
        red, nir, nodata, transform, crs = self._read_clipped_bands(red_href, nir_href, aoi)

        granule_id = str(
            getattr(granule, "id", None)
            or _umm_value(granule, "GranuleUR")
            or _umm_value(granule, "ProducerGranuleId")
            or "unknown"
        )
        acquired = _granule_datetime(granule)

        return RedNirScene(
            red_band=red,
            nir_band=nir,
            nodata_mask=nodata,
            pixel_size_m=_PIXEL_SIZE_M,
            source="hls_ndvi",
            granule_id=granule_id,
            acquired_at=acquired,
            product=_PRODUCT,
            scale_factor=1.0,
            fill_value=None,
            transform=transform,
            crs=crs,
        )

    def _login(self) -> None:
        import earthaccess

        os.environ["EARTHDATA_USERNAME"] = self._settings.nasa_earthaccess_username.strip()
        os.environ["EARTHDATA_PASSWORD"] = self._settings.nasa_earthaccess_password.strip()
        auth = earthaccess.login(strategy="environment")
        if auth is None or (hasattr(auth, "authenticated") and not auth.authenticated):
            raise ValidationError("NASA EarthAccess login failed. Check credentials.")

    def _search_best_granule(self, bbox: tuple[float, float, float, float]) -> Any:
        import earthaccess

        self._login()
        min_lon, min_lat, max_lon, max_lat = bbox
        end = datetime.now(UTC)
        start = end - timedelta(days=self._settings.hls_lookback_days)
        temporal = (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        _log.info(
            "Searching %s for bbox=%s temporal=%s cloud<=%s",
            _PRODUCT,
            bbox,
            temporal,
            self._settings.hls_max_cloud_cover,
        )
        results = earthaccess.search_data(
            short_name=_PRODUCT,
            bounding_box=(min_lon, min_lat, max_lon, max_lat),
            temporal=temporal,
            cloud_cover=(0, self._settings.hls_max_cloud_cover),
            count=25,
        )
        if not results:
            raise ValidationError(
                f"No {_PRODUCT} granules found for AOI in the last "
                f"{self._settings.hls_lookback_days} days "
                f"(cloud ≤ {self._settings.hls_max_cloud_cover}%)."
            )

        ranked = sorted(
            results,
            key=lambda g: (_cloud_cover(g), -_granule_timestamp(g)),
        )
        # earthaccess cloud_cover filter is not always applied; enforce locally.
        max_cloud = float(self._settings.hls_max_cloud_cover)
        usable = [g for g in ranked if _cloud_cover(g) <= max_cloud]
        if not usable:
            raise ValidationError(
                f"No {_PRODUCT} granules with cloud ≤ {max_cloud}% "
                f"for AOI in the last {self._settings.hls_lookback_days} days."
            )
        best = usable[0]
        _log.info(
            "Selected HLS granule cloud=%.1f id=%s",
            _cloud_cover(best),
            getattr(best, "id", None)
            or _umm_value(best, "GranuleUR")
            or "?",
        )
        return best

    def _band_hrefs(self, granule: Any) -> tuple[str, str]:
        links = _data_links(granule)
        red = _find_band_link(links, _RED_BAND)
        nir = _find_band_link(links, _NIR_BAND)
        if not red or not nir:
            raise ValidationError(
                f"HLS granule is missing {_RED_BAND} and/or {_NIR_BAND} assets."
            )
        return red, nir

    def _read_clipped_bands(
        self,
        red_href: str,
        nir_href: str,
        aoi: Any,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[float, ...], str]:
        import earthaccess
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.mask import mask as rio_mask
        from rasterio.warp import reproject

        def _open_href(href: str) -> Any:
            """Open one COG with earthaccess auth; fall back to the bare URL."""

            try:
                opened = list(earthaccess.open([href]))
                if opened:
                    return opened[0]
            except Exception:  # noqa: BLE001
                pass
            return href

        # Open bands separately so Red/NIR order cannot be swapped by bulk open.
        red_src_path = _open_href(red_href)
        nir_src_path = _open_href(nir_href)

        with rasterio.Env():
            with rasterio.open(red_src_path) as red_src:
                aoi_red = _reproject_aoi_to_crs(aoi, red_src.crs)
                red_image, transform = rio_mask(
                    red_src,
                    [mapping(aoi_red)],
                    crop=True,
                    filled=True,
                    nodata=_HLS_FILL,
                )
                red_raw = red_image[0]
                crs = red_src.crs
                crs_str = crs.to_string() if crs else "EPSG:4326"

            with rasterio.open(nir_src_path) as nir_src:
                # Force NIR onto the exact Red grid. Independent crop windows
                # for B04/B8A can differ by a few pixels and invent false NDVI
                # along hard edges (roads / building shadows).
                nir_dest = np.full(red_raw.shape, _HLS_FILL, dtype=np.float64)
                reproject(
                    source=rasterio.band(nir_src, 1),
                    destination=nir_dest,
                    src_transform=nir_src.transform,
                    src_crs=nir_src.crs,
                    dst_transform=transform,
                    dst_crs=crs,
                    dst_nodata=_HLS_FILL,
                    resampling=Resampling.bilinear,
                )
                nir_raw = nir_dest

        nodata = (red_raw == _HLS_FILL) | (nir_raw == _HLS_FILL)
        # Also treat near-fill after bilinear resampling as nodata.
        nodata |= np.isclose(nir_raw, _HLS_FILL, atol=1.0)

        red = red_raw.astype(np.float64) * _HLS_SCALE
        nir = nir_raw.astype(np.float64) * _HLS_SCALE
        red[nodata] = np.nan
        nir[nodata] = np.nan

        if int((~nodata).sum()) == 0:
            raise ValidationError("HLS clip produced no valid pixels inside the AOI.")

        # Affine as 6-tuple for RedNirScene serialisability.
        t = transform
        transform_tuple = (
            float(t.a),
            float(t.b),
            float(t.c),
            float(t.d),
            float(t.e),
            float(t.f),
        )
        return red, nir, nodata, transform_tuple, crs_str


def _umm_value(granule: Any, key: str) -> Any:
    umm = getattr(granule, "umm", None)
    if umm is None and hasattr(granule, "__getitem__"):
        try:
            umm = granule["umm"]
        except Exception:  # noqa: BLE001
            umm = None
    if isinstance(umm, dict):
        return umm.get(key)
    return None


def _umm_additional_attribute(granule: Any, name: str) -> Any:
    """Read an HLS ``AdditionalAttributes`` value by attribute name."""

    attrs = _umm_value(granule, "AdditionalAttributes") or []
    if not isinstance(attrs, list):
        return None
    needle = name.upper()
    for item in attrs:
        if not isinstance(item, dict):
            continue
        if str(item.get("Name") or "").upper() != needle:
            continue
        values = item.get("Values") or []
        if values:
            return values[0]
    return None


def _cloud_cover(granule: Any) -> float:
    """Return cloud coverage percent for ranking (missing → 100)."""

    for candidate in (
        getattr(granule, "cloud_cover", None),
        _umm_value(granule, "CloudCover"),
        _umm_additional_attribute(granule, "CLOUD_COVERAGE"),
        _umm_additional_attribute(granule, "CLOUD_COVER"),
    ):
        if candidate is None:
            continue
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    try:
        meta = granule["umm"]["CloudCover"]  # type: ignore[index]
        return float(meta)
    except Exception:  # noqa: BLE001
        return 100.0


def _granule_timestamp(granule: Any) -> float:
    dt = _granule_datetime(granule)
    if dt is None:
        return 0.0
    return dt.timestamp()


def _granule_datetime(granule: Any) -> datetime | None:
    for key in ("time_start", "beginning_date_time", "BeginningDateTime"):
        raw = getattr(granule, key, None) or _umm_value(granule, key)
        if raw:
            try:
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except ValueError:
                continue
    try:
        temporal = granule["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]  # type: ignore[index]
        return datetime.fromisoformat(str(temporal).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _data_links(granule: Any) -> list[str]:
    links: list[str] = []
    if hasattr(granule, "data_links"):
        try:
            links.extend(list(granule.data_links(access="external")))
        except TypeError:
            links.extend(list(granule.data_links()))
        except Exception:  # noqa: BLE001
            pass
    if not links and hasattr(granule, "data_links"):
        try:
            links.extend(list(granule.data_links(access="direct")))
        except Exception:  # noqa: BLE001
            pass
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique


def _find_band_link(links: list[str], band: str) -> str | None:
    needle = f".{band}.tif"
    for link in links:
        if needle in link or link.endswith(f"{band}.tif"):
            return link
    # Case-insensitive fallback
    lower_needle = needle.lower()
    for link in links:
        if lower_needle in link.lower():
            return link
    return None


def _reproject_aoi_to_crs(aoi: Any, crs: Any) -> Any:
    """Reproject WGS84 AOI into the raster CRS when needed."""

    import rasterio
    from rasterio.warp import transform_geom

    if crs is None:
        return aoi
    crs_obj = rasterio.crs.CRS.from_user_input(crs)
    if crs_obj.to_epsg() == 4326:
        return aoi
    geom = transform_geom("EPSG:4326", crs_obj, mapping(aoi), precision=6)
    return shape(geom)
