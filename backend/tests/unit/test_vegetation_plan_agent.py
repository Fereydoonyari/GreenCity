"""Unit tests for geo climate characterization and vegetation-plan templates."""

from greencity.domain.value_objects.agent_narrative import CityLocation, NeighborhoodSnapshot
from greencity.infrastructure.agent.geo_climate import characterize_location
from greencity.infrastructure.agent.narratives import (
    NeighborhoodAgentNarrator,
    build_template_vegetation_plan,
)


def _snap() -> NeighborhoodSnapshot:
    return NeighborhoodSnapshot(
        id="n1",
        name="Quarter A",
        score=62.0,
        priority_band="high",
        rank=1,
        vegetation_coverage=0.18,
        green_area_per_m2=0.08,
        road_density=12_000.0,
        built_up_ratio=0.7,
    )


def test_characterize_paris_like_location() -> None:
    profile = characterize_location(latitude=48.8566, longitude=2.3522, city_name="Paris")
    assert profile.hemisphere == "northern"
    assert profile.latitude_band == "temperate"
    assert "Paris" in profile.summary
    assert profile.planting_notes


def test_template_vegetation_plan_has_three_horizons() -> None:
    city = CityLocation(name="Paris", latitude=48.8566, longitude=2.3522)
    narrative = build_template_vegetation_plan(city, _snap())
    assert narrative.kind == "vegetation_plan"
    titles = [s.title.lower() for s in narrative.sections]
    assert any("geolocation" in t or "climate" in t for t in titles)
    assert any("short-term" in t for t in titles)
    assert any("mid-term" in t for t in titles)
    assert any("long-term" in t for t in titles)


def test_narrator_vegetation_plan_without_key_uses_template() -> None:
    narrator = NeighborhoodAgentNarrator(api_key="")
    out = narrator.vegetation_plan(
        CityLocation(name="Paris", latitude=48.85, longitude=2.35),
        _snap(),
    )
    assert out.source == "template"
