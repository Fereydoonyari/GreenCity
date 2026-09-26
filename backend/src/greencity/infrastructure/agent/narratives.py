"""LLM / template generators for comprehensive neighborhood agent narratives."""

from __future__ import annotations

import logging

from greencity.config import Settings, get_settings
from greencity.domain.value_objects.agent_narrative import (
    AgentNarrative,
    CityLocation,
    NarrativeSection,
    NeighborhoodSnapshot,
)
from greencity.infrastructure.agent.geo_climate import characterize_location

_log = logging.getLogger(__name__)


def _fmt_pct(value: float) -> str:
    return f"{value:.1%}"


def _fmt_road(value: float) -> str:
    return f"{value:,.0f} m/km²"


def _snapshot_block(snap: NeighborhoodSnapshot) -> str:
    rank = f"rank #{snap.rank}" if snap.rank is not None else "unranked"
    return (
        f"{snap.name}: GDS {snap.score:.1f}/100 ({snap.priority_band}, {rank}); "
        f"vegetation {_fmt_pct(snap.vegetation_coverage)}, "
        f"green area/m² {_fmt_pct(snap.green_area_per_m2)}, "
        f"road density {_fmt_road(snap.road_density)}, "
        f"built-up {_fmt_pct(snap.built_up_ratio)}"
    )


def _openai_chat(*, api_key: str, model: str, system: str, user: str, max_tokens: int) -> str | None:
    from greencity.infrastructure.llm import chat_completion

    text = chat_completion(
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.35,
        max_tokens=max_tokens,
        timeout_s=45.0,
    )
    if not text:
        _log.warning("Agent LLM unavailable; using template")
    return text


def _parse_sections(raw: str, *, fallback_title: str) -> tuple[NarrativeSection, ...]:
    """Parse ``## Heading`` markdown sections from LLM output."""

    lines = raw.replace("\r\n", "\n").split("\n")
    sections: list[NarrativeSection] = []
    current_title = fallback_title
    current_body: list[str] = []

    def flush() -> None:
        body = "\n".join(current_body).strip()
        if body:
            sections.append(NarrativeSection(title=current_title.strip() or fallback_title, body=body))

    for line in lines:
        if line.startswith("## "):
            flush()
            current_title = line[3:].strip()
            current_body = []
        else:
            current_body.append(line)
    flush()
    if sections:
        return tuple(sections)
    return (NarrativeSection(title=fallback_title, body=raw.strip()),)


def build_template_neighborhood_brief(
    focus: NeighborhoodSnapshot,
    peers: tuple[NeighborhoodSnapshot, ...],
) -> AgentNarrative:
    """Deterministic comprehensive brief when LLM is unavailable."""

    peer_bits = []
    for peer in peers:
        if peer.id == focus.id:
            continue
        delta = focus.score - peer.score
        relation = "higher deficiency than" if delta > 0 else "lower deficiency than"
        if abs(delta) < 0.05:
            relation = "similar deficiency to"
        peer_bits.append(f"{relation} {peer.name} ({peer.score:.1f})")

    comparison = (
        "Among your mapped neighborhoods, " + "; ".join(peer_bits) + "."
        if peer_bits
        else "No other scored neighborhoods are available yet for comparison."
    )

    characteristics = (
        f"{focus.name} has a Green Deficiency Score of {focus.score:.1f}/100 "
        f"({focus.priority_band} priority"
        + (f", rank #{focus.rank}" if focus.rank is not None else "")
        + "). "
        f"Vegetation coverage is {_fmt_pct(focus.vegetation_coverage)}, "
        f"green area per m² {_fmt_pct(focus.green_area_per_m2)}, "
        f"road density {_fmt_road(focus.road_density)}, "
        f"and built-up ratio {_fmt_pct(focus.built_up_ratio)}."
    )

    aspects = (
        "Vegetation & canopy: "
        f"{'relatively limited' if focus.vegetation_coverage < 0.35 else 'moderate to strong'} "
        f"coverage ({_fmt_pct(focus.vegetation_coverage)}). "
        "Green land share: "
        f"{'constrained' if focus.green_area_per_m2 < 0.15 else 'more generous'} "
        f"open green fraction ({_fmt_pct(focus.green_area_per_m2)}). "
        "Mobility pressure: "
        f"{'elevated' if focus.road_density > 8000 else 'moderate'} "
        f"road density ({_fmt_road(focus.road_density)}). "
        "Urban fabric: "
        f"{'intensely built-up' if focus.built_up_ratio > 0.55 else 'mixed built form'} "
        f"({_fmt_pct(focus.built_up_ratio)} sealed/built share)."
    )

    return AgentNarrative(
        title=f"Agent brief: {focus.name}",
        kind="neighborhood_brief",
        focus_name=focus.name,
        sections=(
            NarrativeSection(title="Neighborhood character", body=characteristics),
            NarrativeSection(title="Green-infrastructure aspects", body=aspects),
            NarrativeSection(title="Compared with your other neighborhoods", body=comparison),
            NarrativeSection(
                title="Planning takeaway",
                body=(
                    f"Prioritise interventions that address the weakest aspects of {focus.name} "
                    "relative to peers, using the scored indicators above as the factual basis."
                ),
            ),
        ),
        source="template",
    )


def build_template_neighborhood_comparison(
    neighborhoods: tuple[NeighborhoodSnapshot, ...],
) -> AgentNarrative:
    """Deterministic cross-neighborhood comparison when LLM is unavailable."""

    ordered = sorted(neighborhoods, key=lambda n: n.score, reverse=True)
    ranking_lines = "\n".join(
        f"{i + 1}. {n.name} — {n.score:.1f}/100 ({n.priority_band}); "
        f"veg {_fmt_pct(n.vegetation_coverage)}, green {_fmt_pct(n.green_area_per_m2)}, "
        f"roads {_fmt_road(n.road_density)}, built {_fmt_pct(n.built_up_ratio)}"
        for i, n in enumerate(ordered)
    )
    highest = ordered[0]
    lowest = ordered[-1]
    overview = (
        f"Across {len(ordered)} neighborhood(s), green deficiency ranges from "
        f"{lowest.score:.1f} ({lowest.name}) to {highest.score:.1f} ({highest.name}). "
        f"{highest.name} is the highest priority for green investment; "
        f"{lowest.name} currently shows the strongest relative green performance."
    )
    themes = (
        "Common pressures tend to cluster around low vegetation coverage, limited green land "
        "share, dense road networks, and high built-up ratios. Use the ranking and indicator "
        "gaps below to sequence investment across your mapped neighborhoods."
    )
    return AgentNarrative(
        title="Agent comparison: all neighborhoods",
        kind="neighborhood_comparison",
        focus_name=None,
        sections=(
            NarrativeSection(title="Overview", body=overview),
            NarrativeSection(title="Priority ranking & indicators", body=ranking_lines),
            NarrativeSection(title="Cross-cutting themes", body=themes),
        ),
        source="template",
    )


def build_template_vegetation_plan(
    city: CityLocation,
    focus: NeighborhoodSnapshot,
) -> AgentNarrative:
    """Deterministic short / mid / long-term planting plan when LLM is unavailable."""

    climate = characterize_location(
        latitude=city.latitude,
        longitude=city.longitude,
        city_name=city.name,
    )
    neighborhood_ctx = (
        f"{focus.name} scores {focus.score:.1f}/100 ({focus.priority_band} priority) with "
        f"vegetation {_fmt_pct(focus.vegetation_coverage)}, green area/m² "
        f"{_fmt_pct(focus.green_area_per_m2)}, road density {_fmt_road(focus.road_density)}, "
        f"and built-up {_fmt_pct(focus.built_up_ratio)}. "
        "Use vacant strips, courtyards, and street edges where deficiency is highest."
    )
    short_term = (
        "Short term (0–24 months): establish quick green cover with hardy groundcovers, "
        "ornamental grasses, and fast shrubs/bushes suited to a "
        f"{climate.climate_label} setting. Prioritise low-cost pocket plantings, planter "
        "boxes, and living hedges along high road-density edges to cut heat and improve "
        "perceived greenery while trees establish."
    )
    mid_term = (
        "Mid term (2–7 years): expand multi-stem shrubs, flowering bushes, and pioneer / "
        "fast-growing small trees that tolerate local seasons. Create green corridors "
        "linking parks and streets; replace failed short-term stock; thin crowded bushes "
        "so longer-lived canopy trees have light and rooting space."
    )
    long_term = (
        "Long term (7–30+ years): plant and protect climate-suitable canopy trees for "
        f"{climate.climate_label} conditions ({climate.latitude_band.replace('_', ' ')} band). "
        "Favour regional natives or proven urban cultivars with adequate soil volume, "
        "drought/heat resilience, and space away from utilities. Maintain a succession "
        "plan so mature canopy replaces aging stock without loss of shade."
    )
    return AgentNarrative(
        title=f"Vegetation plan: {focus.name}",
        kind="vegetation_plan",
        focus_name=focus.name,
        sections=(
            NarrativeSection(title="City geolocation & climate character", body=climate.summary + " " + climate.planting_notes),
            NarrativeSection(title="Neighborhood green context", body=neighborhood_ctx),
            NarrativeSection(title="Short-term plan (fast cover)", body=short_term),
            NarrativeSection(title="Mid-term plan (bushes & pioneers)", body=mid_term),
            NarrativeSection(title="Long-term plan (canopy trees)", body=long_term),
        ),
        source="template",
    )


class NeighborhoodAgentNarrator:
    """Produce neighborhood briefs, comparisons, and vegetation plans."""

    def __init__(self, *, api_key: str = "", model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key.strip()
        self._model = model

    def neighborhood_brief(
        self,
        focus: NeighborhoodSnapshot,
        peers: tuple[NeighborhoodSnapshot, ...],
    ) -> AgentNarrative:
        template = build_template_neighborhood_brief(focus, peers)
        if not self._api_key:
            return template

        peer_text = "\n".join(
            f"- {_snapshot_block(p)}" for p in peers if p.id != focus.id
        ) or "- (no other neighborhoods scored yet)"
        prompt = (
            "Write a complete, comprehensive urban green-infrastructure analysis of ONE "
            "neighborhood for city planners. Use ONLY the numbers provided — never invent "
            "metrics. Cover: (1) overall character, (2) vegetation/green land/road/built-up "
            "aspects, (3) how it compares to the other listed neighborhoods, (4) practical "
            "planning implications.\n\n"
            "Format with markdown ## section headings (4 sections).\n\n"
            f"Focus neighborhood:\n- {_snapshot_block(focus)}\n\n"
            f"Other neighborhoods:\n{peer_text}"
        )
        raw = _openai_chat(
            api_key=self._api_key,
            model=self._model,
            system=(
                "You are GreenCity AI, an urban green-infrastructure planning agent. "
                "Be thorough, clear, and strictly grounded in provided scores/indicators."
            ),
            user=prompt,
            max_tokens=900,
        )
        if not raw:
            return template
        return AgentNarrative(
            title=f"Agent brief: {focus.name}",
            kind="neighborhood_brief",
            focus_name=focus.name,
            sections=_parse_sections(raw, fallback_title="Analysis"),
            source="llm_augmented",
        )

    def neighborhood_comparison(
        self,
        neighborhoods: tuple[NeighborhoodSnapshot, ...],
    ) -> AgentNarrative:
        template = build_template_neighborhood_comparison(neighborhoods)
        if not self._api_key:
            return template

        roster = "\n".join(f"- {_snapshot_block(n)}" for n in neighborhoods)
        prompt = (
            "Compare ALL of the user's mapped neighborhoods comprehensively. Use ONLY the "
            "numbers provided. Cover: (1) overview of relative green deficiency, (2) ranked "
            "characteristics and standout differences, (3) shared strengths/weaknesses, "
            "(4) how to prioritise investment across the set.\n\n"
            "Format with markdown ## section headings (4 sections).\n\n"
            f"Neighborhoods:\n{roster}"
        )
        raw = _openai_chat(
            api_key=self._api_key,
            model=self._model,
            system=(
                "You are GreenCity AI, an urban green-infrastructure planning agent. "
                "Write a thorough comparative briefing grounded only in provided data."
            ),
            user=prompt,
            max_tokens=1100,
        )
        if not raw:
            return template
        return AgentNarrative(
            title="Agent comparison: all neighborhoods",
            kind="neighborhood_comparison",
            focus_name=None,
            sections=_parse_sections(raw, fallback_title="Comparison"),
            source="llm_augmented",
        )

    def vegetation_plan(
        self,
        city: CityLocation,
        focus: NeighborhoodSnapshot,
    ) -> AgentNarrative:
        template = build_template_vegetation_plan(city, focus)
        climate = characterize_location(
            latitude=city.latitude,
            longitude=city.longitude,
            city_name=city.name,
        )
        if not self._api_key:
            return template

        prompt = (
            "You are an urban vegetation planning agent. Using the city coordinates and "
            "coarse climate framing plus the neighborhood indicator scores, write a practical "
            "planting plan. Do NOT invent indicator numbers. Propose plant TYPES suited to the "
            "climate (you may name common regional genera/species as examples, noting they must "
            "be verified locally). Structure with markdown ## headings for exactly these 5 "
            "sections:\n"
            "1) City geolocation & climate character\n"
            "2) Neighborhood green context\n"
            "3) Short-term plan (fast cover) — 0–24 months: grasses, groundcovers, fast bushes\n"
            "4) Mid-term plan (bushes & pioneers) — 2–7 years: shrubs, hedges, fast-growing trees\n"
            "5) Long-term plan (canopy trees) — 7–30+ years: climate-suitable shade/canopy trees\n\n"
            f"City: {city.name} at lat {city.latitude:.5f}, lon {city.longitude:.5f}\n"
            f"Climate framing: {climate.climate_label} ({climate.latitude_band}, "
            f"{climate.hemisphere} hemisphere)\n"
            f"Climate notes: {climate.planting_notes}\n"
            f"Geo summary: {climate.summary}\n\n"
            f"Neighborhood facts:\n- {_snapshot_block(focus)}\n"
        )
        raw = _openai_chat(
            api_key=self._api_key,
            model=self._model,
            system=(
                "You are GreenCity AI, a vegetation planning agent. Ground every recommendation "
                "in the provided coordinates, climate framing, and indicator scores. Be concrete "
                "about short-, mid-, and long-term planting stages."
            ),
            user=prompt,
            max_tokens=1200,
        )
        if not raw:
            return template
        return AgentNarrative(
            title=f"Vegetation plan: {focus.name}",
            kind="vegetation_plan",
            focus_name=focus.name,
            sections=_parse_sections(raw, fallback_title="Vegetation plan"),
            source="llm_augmented",
        )


def build_neighborhood_agent_narrator(
    settings: Settings | None = None,
) -> NeighborhoodAgentNarrator:
    """Factory from app settings."""

    resolved = settings or get_settings()
    return NeighborhoodAgentNarrator(
        api_key=resolved.openai_api_key,
        model=resolved.llm_model,
    )
