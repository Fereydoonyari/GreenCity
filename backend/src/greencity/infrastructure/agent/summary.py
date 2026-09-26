"""Short analysis summary helper (kept for compatibility / unit tests).

Prefer ``domain.value_objects.report.build_explainable_report`` and the
``ReportExplainerPort`` adapters for full explainable reports.
"""

from __future__ import annotations

from typing import Any


def build_analysis_summary(
    *,
    score: float,
    priority_band: str,
    contributions: list[dict[str, Any]],
) -> str:
    """Build a short deterministic narrative from GDS contributions."""

    ranked = sorted(
        contributions,
        key=lambda c: float(c.get("weighted_contribution", 0.0)),
        reverse=True,
    )
    top = ranked[:3]
    drivers = ", ".join(
        f"{c['key']} ({float(c['weighted_contribution']) * 100:.1f} pts)" for c in top
    )
    return (
        f"Green Deficiency Score is {score:.1f}/100 ({priority_band} priority). "
        f"Top contributing factors: {drivers}."
    )
