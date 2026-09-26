"""Unit tests for agent neighborhood narratives (template path)."""

from greencity.domain.value_objects.agent_narrative import NeighborhoodSnapshot
from greencity.infrastructure.agent.narratives import (
    NeighborhoodAgentNarrator,
    build_template_neighborhood_brief,
    build_template_neighborhood_comparison,
)


def _snap(name: str, score: float, *, nid: str | None = None) -> NeighborhoodSnapshot:
    return NeighborhoodSnapshot(
        id=nid or name.lower(),
        name=name,
        score=score,
        priority_band="high" if score >= 60 else "medium" if score >= 40 else "low",
        rank=None,
        vegetation_coverage=0.2,
        green_area_per_m2=0.1,
        road_density=9000.0,
        built_up_ratio=0.6,
    )


def test_template_brief_mentions_focus_and_peers() -> None:
    focus = _snap("Alpha", 72.0)
    peers = (focus, _snap("Beta", 40.0), _snap("Gamma", 55.0))
    narrative = build_template_neighborhood_brief(focus, peers)
    assert narrative.kind == "neighborhood_brief"
    assert narrative.focus_name == "Alpha"
    assert narrative.source == "template"
    joined = " ".join(s.body for s in narrative.sections)
    assert "Alpha" in joined
    assert "Beta" in joined


def test_template_comparison_orders_by_score() -> None:
    neighborhoods = (_snap("Low", 20.0), _snap("High", 80.0), _snap("Mid", 50.0))
    narrative = build_template_neighborhood_comparison(neighborhoods)
    assert narrative.kind == "neighborhood_comparison"
    ranking = next(s for s in narrative.sections if "ranking" in s.title.lower())
    assert ranking.body.index("High") < ranking.body.index("Mid") < ranking.body.index("Low")


def test_narrator_without_api_key_uses_template() -> None:
    narrator = NeighborhoodAgentNarrator(api_key="", model="gpt-4o-mini")
    focus = _snap("N1", 61.0)
    out = narrator.neighborhood_brief(focus, (focus,))
    assert out.source == "template"
    compare = narrator.neighborhood_comparison((focus, _snap("N2", 30.0)))
    assert compare.source == "template"
