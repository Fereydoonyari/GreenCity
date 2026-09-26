"""Unit tests for explainable report domain builders."""

from greencity.domain.services.scoring import compute_green_deficiency_score
from greencity.domain.value_objects.indicator_weights import IndicatorWeights
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.domain.value_objects.report import build_explainable_report
from greencity.infrastructure.reporting import (
    LlmAugmentedReportExplainer,
    TemplateReportExplainer,
)


def _score():
    indicators = IndicatorValues(
        vegetation_coverage=0.15,
        green_area_per_m2=0.1,
        road_density=12_000.0,
        built_up_ratio=0.7,
    )
    weights = IndicatorWeights.balanced_default()
    return compute_green_deficiency_score(indicators, weights), indicators


def test_build_explainable_report_structure() -> None:
    score, indicators = _score()
    report = build_explainable_report(score, indicators, aoi_name="North Ward")

    assert "North Ward" in report.headline
    assert report.priority_band in {"low", "medium", "high"}
    assert report.score == score.score
    assert len(report.drivers) == 4
    assert len(report.recommendations) >= 1
    assert "normalisation" in report.methodology_notes.lower() or "Normalisation" in report.methodology_notes
    assert report.source == "template"


def test_template_explainer() -> None:
    score, indicators = _score()
    content = TemplateReportExplainer().explain(score, indicators, aoi_name="Zone A")
    assert "Zone A" in content.executive_summary
    assert content.drivers[0].weighted_points >= content.drivers[-1].weighted_points


def test_llm_explainer_falls_back_without_narrative() -> None:
    score, indicators = _score()
    explainer = LlmAugmentedReportExplainer(narrative=None)
    content = explainer.explain(score, indicators, aoi_name="Zone B")
    assert content.source == "template"


def test_llm_explainer_uses_override() -> None:
    class _Stub:
        def generate(self, template, *, aoi_name: str) -> str | None:
            return f"LLM summary for {aoi_name}."

    score, indicators = _score()
    content = LlmAugmentedReportExplainer(narrative=_Stub()).explain(
        score, indicators, aoi_name="Central"
    )
    assert content.source == "llm_augmented"
    assert content.executive_summary == "LLM summary for Central."
