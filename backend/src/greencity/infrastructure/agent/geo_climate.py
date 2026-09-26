"""Deterministic climate / geolocation character from lat-lon (no external API)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeoClimateProfile:
    """Coarse climate/context tags derived from latitude (and rough longitude band)."""

    hemisphere: str
    latitude_band: str
    climate_label: str
    planting_notes: str
    summary: str


def characterize_location(*, latitude: float, longitude: float, city_name: str) -> GeoClimateProfile:
    """Map WGS84 coordinates to a coarse climate character for planting guidance."""

    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be between -90 and 90.")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("longitude must be between -180 and 180.")

    hemisphere = "northern" if latitude >= 0 else "southern"
    abs_lat = abs(latitude)

    if abs_lat < 10:
        band, climate = "equatorial", "humid tropical / equatorial"
        notes = (
            "Year-round growing season; prioritize heat- and humidity-tolerant species, "
            "deep shade trees, and storm-resilient rooting. Avoid frost-tender assumptions "
            "only if elevation is high."
        )
    elif abs_lat < 23.5:
        band, climate = "tropical", "tropical"
        notes = (
            "Long warm season; favor drought-tolerant evergreens where dry seasons occur, "
            "fast shrubs for short-term cover, and canopy trees suited to intense sun."
        )
    elif abs_lat < 35:
        band, climate = "subtropical", "subtropical / warm-temperate"
        notes = (
            "Mild winters in lowlands; mix drought-aware Mediterranean or monsoon-adapted "
            "palettes. Use fast hedges short-term; plant longer-lived shade trees with room to mature."
        )
    elif abs_lat < 50:
        band, climate = "temperate", "temperate"
        notes = (
            "Distinct seasons; choose species hardy to local winter lows. Short-term: grasses "
            "and flowering shrubs; mid-term: hedges and pioneer trees; long-term: native canopy "
            "oaks, maples, limes, or regional equivalents."
        )
    elif abs_lat < 60:
        band, climate = "cool_temperate", "cool temperate / continental fringe"
        notes = (
            "Shorter growing season and colder winters; prefer cold-hardy natives, wind shelter "
            "belts, and trees that establish before canopy maturity (10–30+ years)."
        )
    else:
        band, climate = "boreal_polar", "boreal / subpolar"
        notes = (
            "Short cool summers; focus on hardy pioneer shrubs and cold-tolerant conifers; "
            "long-term canopy is slow—protect existing vegetation and plant in sheltered microclimates."
        )

    lon_hint = ""
    if  -30 <= longitude <= 60 and 30 <= abs_lat <= 50:
        lon_hint = " Coordinates fall in a Europe–Mediterranean / western Asia belt—check local drought and heat extremes."
    elif -130 <= longitude <= -60 and 25 <= abs_lat <= 55:
        lon_hint = " Coordinates fall in a North American mid-latitude belt—match USDA/hardiness and regional natives."
    elif 60 <= longitude <= 150 and abs_lat < 50:
        lon_hint = " Coordinates fall across Asia—verify monsoon vs continental drought regimes locally."

    summary = (
        f"{city_name} is centered near {latitude:.4f}°, {longitude:.4f}° "
        f"({hemisphere} hemisphere, {band.replace('_', ' ')} latitude band). "
        f"Coarse climate framing: {climate}.{lon_hint}"
    )
    return GeoClimateProfile(
        hemisphere=hemisphere,
        latitude_band=band,
        climate_label=climate,
        planting_notes=notes,
        summary=summary,
    )
