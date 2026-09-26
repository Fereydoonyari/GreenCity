"""LangGraph StateGraph for GreenCity analysis orchestration.

Nodes call injected callables that wrap application use cases / domain
services. The summarise node builds a structured explainable report
(template by default; optional LLM narrative via ReportExplainerPort).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from greencity.infrastructure.agent.state import AnalysisGraphState

# Callable contracts injected by the orchestrator.
ProgressFn = Callable[[UUID, str, int], None]
ValidateFn = Callable[[UUID], dict[str, Any]]
ComputeIndicatorsFn = Callable[..., dict[str, Any]]
ScoreFn = Callable[..., dict[str, Any]]
ExplainFn = Callable[..., dict[str, Any]]


def build_analysis_graph(
    *,
    validate: ValidateFn,
    compute_indicators: ComputeIndicatorsFn,
    score: ScoreFn,
    explain: ExplainFn,
    update_progress: ProgressFn,
) -> Any:
    """Compile the deterministic analysis StateGraph.

    Graph:
      validate → indicators → score → summarise → END
    """

    def node_validate(state: AnalysisGraphState) -> AnalysisGraphState:
        job_id = UUID(state["job_id"])
        update_progress(job_id, "validate_inputs", 10)
        meta = validate(job_id)
        steps = list(state.get("steps_completed") or [])
        steps.append("validate_inputs")
        return {
            **state,
            "aoi_id": meta["aoi_id"],
            "scoring_profile_id": meta["scoring_profile_id"],
            "aoi_name": meta.get("aoi_name", "the study area"),
            "current_step": "validate_inputs",
            "progress_pct": 10,
            "steps_completed": steps,
            "error": None,
        }

    def node_indicators(state: AnalysisGraphState) -> AnalysisGraphState:
        job_id = UUID(state["job_id"])
        update_progress(job_id, "compute_indicators", 45)
        payload = compute_indicators(
            aoi_id=UUID(state["aoi_id"]),
            vegetation_coverage=state.get("vegetation_coverage"),
            green_area_m2=state.get("green_area_m2"),
            park_walk_distance_m=float(state.get("park_walk_distance_m") or 300.0),
        )
        steps = list(state.get("steps_completed") or [])
        steps.append("compute_indicators")
        return {
            **state,
            "indicators": payload["indicators"],
            "vegetation_source": payload["vegetation_source"],
            "green_area_source": payload["green_area_source"],
            "vegetation_mask": payload.get("vegetation_mask"),
            "vegetation_hotspot_mask": payload.get("vegetation_hotspot_mask"),
            "park_access_mask": payload.get("park_access_mask"),
            "heat_exposure_mask": payload.get("heat_exposure_mask"),
            "mean_nearest_park_distance_m": payload.get("mean_nearest_park_distance_m"),
            "median_nearest_park_distance_m": payload.get(
                "median_nearest_park_distance_m"
            ),
            "mean_nearest_park_walk_min": payload.get("mean_nearest_park_walk_min"),
            "median_nearest_park_walk_min": payload.get("median_nearest_park_walk_min"),
            "mean_lst_c": payload.get("mean_lst_c"),
            "heat_source": payload.get("heat_source") or "",
            "current_step": "compute_indicators",
            "progress_pct": 45,
            "steps_completed": steps,
        }

    def node_score(state: AnalysisGraphState) -> AnalysisGraphState:
        job_id = UUID(state["job_id"])
        update_progress(job_id, "compute_gds", 75)
        payload = score(
            indicators=state["indicators"],
            scoring_profile_id=UUID(state["scoring_profile_id"]),
        )
        steps = list(state.get("steps_completed") or [])
        steps.append("compute_gds")
        return {
            **state,
            "score": payload["score"],
            "priority_band": payload["priority_band"],
            "normalisation": payload["normalisation"],
            "contributions": payload["contributions"],
            "current_step": "compute_gds",
            "progress_pct": 75,
            "steps_completed": steps,
        }

    def node_summarise(state: AnalysisGraphState) -> AnalysisGraphState:
        job_id = UUID(state["job_id"])
        update_progress(job_id, "summarise", 90)
        payload = explain(
            job_id=job_id,
            aoi_id=UUID(state["aoi_id"]),
            scoring_profile_id=UUID(state["scoring_profile_id"]),
            aoi_name=str(state.get("aoi_name") or "the study area"),
            indicators=state["indicators"],
            score=float(state.get("score") or 0.0),
            priority_band=str(state.get("priority_band") or "low"),
            normalisation=str(state.get("normalisation") or "benchmarks"),
            contributions=list(state.get("contributions") or []),
        )
        steps = list(state.get("steps_completed") or [])
        steps.append("summarise")
        return {
            **state,
            "summary": payload["summary"],
            "report_id": payload["report_id"],
            "current_step": "summarise",
            "progress_pct": 90,
            "steps_completed": steps,
        }

    graph: StateGraph = StateGraph(AnalysisGraphState)
    graph.add_node("validate", node_validate)
    graph.add_node("indicators", node_indicators)
    graph.add_node("score", node_score)
    graph.add_node("summarise", node_summarise)

    graph.add_edge(START, "validate")
    graph.add_edge("validate", "indicators")
    graph.add_edge("indicators", "score")
    graph.add_edge("score", "summarise")
    graph.add_edge("summarise", END)

    return graph.compile()
