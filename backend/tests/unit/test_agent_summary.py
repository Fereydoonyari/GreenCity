"""Unit tests for analysis summary helper."""

from greencity.infrastructure.agent.summary import build_analysis_summary


def test_build_analysis_summary_includes_score_and_drivers() -> None:
    text = build_analysis_summary(
        score=72.5,
        priority_band="high",
        contributions=[
            {"key": "built_up_ratio", "weighted_contribution": 0.2},
            {"key": "vegetation_coverage", "weighted_contribution": 0.15},
            {"key": "road_density", "weighted_contribution": 0.1},
        ],
    )
    assert "72.5/100" in text
    assert "high priority" in text
    assert "built_up_ratio" in text
