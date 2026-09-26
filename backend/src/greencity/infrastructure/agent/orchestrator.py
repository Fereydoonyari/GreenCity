"""LangGraph implementation of ``AnalysisOrchestratorPort``."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from greencity.application.use_cases.indicators import (
    ComputeIndicatorsCommand,
    ComputeIndicatorsUseCase,
)
from greencity.domain.entities.analysis_job import AnalysisJobStatus
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.exceptions import ConflictError, NotFoundError
from greencity.domain.ports.imagery import ImageryAcquisitionPort
from greencity.domain.ports.indicators import ParkAccessibilityPort
from greencity.domain.ports.reporting import ReportExplainerPort
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.ports.thermal import ThermalAcquisitionPort
from greencity.domain.ports.urban_context import OsmDataPort
from greencity.domain.ports.vegetation import VegetationPipelinePort
from greencity.domain.services.scoring import (
    GreenDeficiencyScore,
    IndicatorContribution,
    IndicatorDirection,
    compute_green_deficiency_score,
)
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.domain.value_objects.orchestration import AnalysisOrchestrationResult
from greencity.infrastructure.agent.graph import build_analysis_graph
from greencity.infrastructure.reporting import TemplateReportExplainer

_log = logging.getLogger(__name__)


class LangGraphAnalysisOrchestrator:
    """Run the analysis StateGraph for a single ``RUNNING`` job.

    Uses one request-scoped ``UnitOfWork`` so progress updates, report
    persistence, and completion stay consistent. OSM / park / imagery /
    explainer ports are injected for tests.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        osm: OsmDataPort,
        park_accessibility: ParkAccessibilityPort,
        explainer: ReportExplainerPort | None = None,
        imagery: ImageryAcquisitionPort | None = None,
        vegetation_pipeline: VegetationPipelinePort | None = None,
        thermal: ThermalAcquisitionPort | None = None,
    ) -> None:
        self._uow = uow
        self._osm = osm
        self._park_accessibility = park_accessibility
        self._explainer = explainer or TemplateReportExplainer()
        self._imagery = imagery
        self._vegetation_pipeline = vegetation_pipeline
        self._thermal = thermal

    def run(
        self,
        job_id: UUID,
        *,
        vegetation_coverage: float | None = None,
        green_area_m2: float | None = None,
        park_walk_distance_m: float = 300.0,
    ) -> AnalysisOrchestrationResult:
        """Execute the LangGraph pipeline and complete/fail the job."""

        graph = build_analysis_graph(
            validate=self._validate,
            compute_indicators=self._compute_indicators,
            score=self._score,
            explain=self._explain,
            update_progress=self._update_progress,
        )

        initial = {
            "job_id": str(job_id),
            "vegetation_coverage": vegetation_coverage,
            "green_area_m2": green_area_m2,
            "park_walk_distance_m": park_walk_distance_m,
            "steps_completed": [],
            "error": None,
        }

        try:
            final: dict[str, Any] = graph.invoke(initial)
        except Exception as exc:  # noqa: BLE001
            _log.exception("Analysis orchestration failed for job %s", job_id)
            self._fail_job(job_id, str(exc) or "Orchestration error.")
            raise

        result = self._to_result(final)
        self._complete_job(job_id)
        return result

    def _validate(self, job_id: UUID) -> dict[str, Any]:
        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        if job.status != AnalysisJobStatus.RUNNING:
            raise ConflictError(
                f"Job must be RUNNING to orchestrate "
                f"(current status: '{job.status.value}')."
            )
        aoi = self._uow.areas_of_interest.get_by_id(job.aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{job.aoi_id}' was not found.")
        profile = self._uow.scoring_profiles.get_by_id(job.scoring_profile_id)
        if profile is None:
            raise NotFoundError(
                f"Scoring profile '{job.scoring_profile_id}' was not found."
            )
        return {
            "aoi_id": str(job.aoi_id),
            "scoring_profile_id": str(job.scoring_profile_id),
            "aoi_name": aoi.name,
        }

    def _compute_indicators(
        self,
        *,
        aoi_id: UUID,
        vegetation_coverage: float | None,
        green_area_m2: float | None,
        park_walk_distance_m: float,
    ) -> dict[str, Any]:
        uc = ComputeIndicatorsUseCase(
            self._uow,
            self._osm,
            self._park_accessibility,
            imagery=self._imagery,
            vegetation_pipeline=self._vegetation_pipeline,
            thermal=self._thermal,
        )
        result = uc.execute(
            ComputeIndicatorsCommand(
                aoi_id=aoi_id,
                vegetation_coverage=vegetation_coverage,
                green_area_m2=green_area_m2,
                park_walk_distance_m=park_walk_distance_m,
            )
        )
        return {
            "indicators": result.indicators.as_dict(),
            "vegetation_source": result.vegetation_source,
            "green_area_source": result.green_area_source,
            "vegetation_mask": result.vegetation_mask,
            "vegetation_hotspot_mask": result.vegetation_hotspot_mask,
            "park_access_mask": result.park_access_mask,
            "heat_exposure_mask": result.heat_exposure_mask,
            "mean_nearest_park_distance_m": result.mean_nearest_park_distance_m,
            "median_nearest_park_distance_m": result.median_nearest_park_distance_m,
            "mean_nearest_park_walk_min": result.mean_nearest_park_walk_min,
            "median_nearest_park_walk_min": result.median_nearest_park_walk_min,
            "mean_lst_c": result.mean_lst_c,
            "heat_source": result.heat_source,
        }

    def _score(
        self,
        *,
        indicators: dict[str, float],
        scoring_profile_id: UUID,
    ) -> dict[str, Any]:
        profile = self._uow.scoring_profiles.get_by_id(scoring_profile_id)
        if profile is None:
            raise NotFoundError(
                f"Scoring profile '{scoring_profile_id}' was not found."
            )
        values = IndicatorValues.from_mapping(indicators)
        gds = compute_green_deficiency_score(values, profile.weights)
        return {
            "score": gds.score,
            "priority_band": gds.priority_band,
            "normalisation": gds.normalisation,
            "contributions": [
                {
                    "key": c.key,
                    "raw_value": c.raw_value,
                    "normalised": c.normalised,
                    "deficiency_component": c.deficiency_component,
                    "weight": c.weight,
                    "weighted_contribution": c.weighted_contribution,
                    "direction": c.direction.value,
                }
                for c in gds.contributions
            ],
        }

    def _explain(
        self,
        *,
        job_id: UUID,
        aoi_id: UUID,
        scoring_profile_id: UUID,
        aoi_name: str,
        indicators: dict[str, float],
        score: float,
        priority_band: str,
        normalisation: str,
        contributions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        values = IndicatorValues.from_mapping(indicators)
        contribs = tuple(
            IndicatorContribution(
                key=c["key"],
                raw_value=float(c["raw_value"]),
                normalised=float(c["normalised"]),
                deficiency_component=float(c["deficiency_component"]),
                weight=float(c["weight"]),
                weighted_contribution=float(c["weighted_contribution"]),
                direction=IndicatorDirection(c["direction"]),
            )
            for c in contributions
        )
        gds = GreenDeficiencyScore(
            score=score,
            contributions=contribs,
            normalisation=normalisation,
        )
        # priority_band is derived from score; keep unused arg for graph clarity
        _ = priority_band
        content = self._explainer.explain(gds, values, aoi_name=aoi_name)
        report = AnalysisReport.from_content(
            analysis_job_id=job_id,
            aoi_id=aoi_id,
            scoring_profile_id=scoring_profile_id,
            content=content,
        )
        saved = self._uow.analysis_reports.add(report)
        self._uow.commit()
        return {
            "summary": saved.executive_summary,
            "report_id": str(saved.id),
        }

    def _update_progress(self, job_id: UUID, step: str, pct: int) -> None:
        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None or job.status != AnalysisJobStatus.RUNNING:
            return
        job.update_progress(current_step=step, progress_pct=pct)
        self._uow.analysis_jobs.save(job)
        self._uow.commit()

    def _complete_job(self, job_id: UUID) -> None:
        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            return
        if job.status == AnalysisJobStatus.RUNNING:
            job.complete()
            self._uow.analysis_jobs.save(job)
            self._uow.commit()

    def _fail_job(self, job_id: UUID, message: str) -> None:
        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            return
        if job.status in {AnalysisJobStatus.QUEUED, AnalysisJobStatus.RUNNING}:
            job.fail(message[:500])
            self._uow.analysis_jobs.save(job)
            self._uow.commit()

    def _to_result(self, final: dict[str, Any]) -> AnalysisOrchestrationResult:
        indicators = IndicatorValues.from_mapping(final["indicators"])
        contributions = tuple(
            IndicatorContribution(
                key=c["key"],
                raw_value=float(c["raw_value"]),
                normalised=float(c["normalised"]),
                deficiency_component=float(c["deficiency_component"]),
                weight=float(c["weight"]),
                weighted_contribution=float(c["weighted_contribution"]),
                direction=IndicatorDirection(c["direction"]),
            )
            for c in final.get("contributions") or []
        )
        gds = GreenDeficiencyScore(
            score=float(final["score"]),
            contributions=contributions,
            normalisation=str(final.get("normalisation") or "benchmarks"),
        )
        report: AnalysisReport | None = None
        report_id = final.get("report_id")
        if report_id:
            report = self._uow.analysis_reports.get_by_id(UUID(str(report_id)))
        return AnalysisOrchestrationResult(
            job_id=UUID(final["job_id"]),
            aoi_id=UUID(final["aoi_id"]),
            scoring_profile_id=UUID(final["scoring_profile_id"]),
            indicators=indicators,
            score=gds,
            steps_completed=tuple(final.get("steps_completed") or []),
            summary=str(final.get("summary") or ""),
            vegetation_source=str(final.get("vegetation_source") or ""),
            green_area_source=str(final.get("green_area_source") or ""),
            report=report,
            vegetation_mask=final.get("vegetation_mask"),
            vegetation_hotspot_mask=final.get("vegetation_hotspot_mask"),
            park_access_mask=final.get("park_access_mask"),
            heat_exposure_mask=final.get("heat_exposure_mask"),
            mean_nearest_park_distance_m=final.get("mean_nearest_park_distance_m"),
            median_nearest_park_distance_m=final.get("median_nearest_park_distance_m"),
            mean_nearest_park_walk_min=final.get("mean_nearest_park_walk_min"),
            median_nearest_park_walk_min=final.get("median_nearest_park_walk_min"),
            mean_lst_c=final.get("mean_lst_c"),
            heat_source=str(final.get("heat_source") or ""),
        )
