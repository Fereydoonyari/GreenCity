"""Template and optional LLM-backed report explainers."""

from __future__ import annotations

import logging
from typing import Protocol

from greencity.config import Settings, get_settings
from greencity.domain.services.scoring import GreenDeficiencyScore
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.domain.value_objects.report import (
    ExplainableReportContent,
    build_explainable_report,
)
from greencity.infrastructure.llm import chat_completion

_log = logging.getLogger(__name__)


class TemplateReportExplainer:
    """Deterministic explainable report from the GDS contribution breakdown."""

    def explain(
        self,
        score: GreenDeficiencyScore,
        indicators: IndicatorValues,
        *,
        aoi_name: str = "the study area",
    ) -> ExplainableReportContent:
        return build_explainable_report(score, indicators, aoi_name=aoi_name, source="template")


class _NarrativeGenerator(Protocol):
    def generate(self, template: ExplainableReportContent, *, aoi_name: str) -> str | None:
        """Return an enriched executive summary, or ``None`` to keep the template."""

        ...


class OpenAiNarrativeGenerator:
    """Optional Chat Completions call; failures fall back to the template."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key.strip()
        self._model = model

    def generate(self, template: ExplainableReportContent, *, aoi_name: str) -> str | None:
        if not self._api_key:
            return None

        drivers = "\n".join(
            f"- {d.label}: {d.weighted_points:.1f} pts — {d.explanation}" for d in template.drivers[:4]
        )
        prompt = (
            "You are an urban green-infrastructure planner. Rewrite the executive "
            "summary below in clear prose for city officials. Do not invent numbers "
            "or drivers not listed. Keep under 120 words.\n\n"
            f"AOI: {aoi_name}\n"
            f"Score: {template.score:.1f}/100 ({template.priority_band})\n"
            f"Drivers:\n{drivers}\n\n"
            f"Template summary:\n{template.executive_summary}"
        )
        text = chat_completion(
            api_key=self._api_key,
            model=self._model,
            messages=[
                {"role": "system", "content": "You write concise planning narratives."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=220,
            timeout_s=30.0,
        )
        if not text:
            _log.warning("LLM narrative unavailable; using template")
        return text


class LlmAugmentedReportExplainer:
    """Template report with optional LLM-rewritten executive summary."""

    def __init__(
        self,
        *,
        template: TemplateReportExplainer | None = None,
        narrative: _NarrativeGenerator | None = None,
    ) -> None:
        self._template = template or TemplateReportExplainer()
        self._narrative = narrative

    def explain(
        self,
        score: GreenDeficiencyScore,
        indicators: IndicatorValues,
        *,
        aoi_name: str = "the study area",
    ) -> ExplainableReportContent:
        base = self._template.explain(score, indicators, aoi_name=aoi_name)
        if self._narrative is None:
            return base
        override = self._narrative.generate(base, aoi_name=aoi_name)
        if not override:
            return base
        return build_explainable_report(
            score,
            indicators,
            aoi_name=aoi_name,
            narrative_override=override,
            source="llm_augmented",
        )


def build_report_explainer(settings: Settings | None = None) -> TemplateReportExplainer | LlmAugmentedReportExplainer:
    """Compose a report explainer from settings (LLM only when API key is set)."""

    resolved = settings or get_settings()
    template = TemplateReportExplainer()
    if not resolved.openai_api_key.strip():
        return template
    return LlmAugmentedReportExplainer(
        template=template,
        narrative=OpenAiNarrativeGenerator(
            api_key=resolved.openai_api_key,
            model=resolved.llm_model,
        ),
    )
