"""Explainable-report adapters (template + optional LLM)."""

from greencity.infrastructure.reporting.explainer import (
    LlmAugmentedReportExplainer,
    TemplateReportExplainer,
    build_report_explainer,
)

__all__ = [
    "LlmAugmentedReportExplainer",
    "TemplateReportExplainer",
    "build_report_explainer",
]
