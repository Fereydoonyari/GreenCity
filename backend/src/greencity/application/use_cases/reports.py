"""Use cases for explainable analysis reports."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.application.use_cases.scoring import ScoreAoiCommand, ScoreAoiUseCase
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.exceptions import NotFoundError, ValidationError
from greencity.domain.ports.reporting import ReportExplainerPort
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.services.scoring import GreenDeficiencyScore
from greencity.domain.value_objects.indicators import IndicatorValues
from greencity.domain.value_objects.report import ExplainableReportContent


@dataclass(frozen=True)
class GenerateReportCommand:
    """Generate (or replace) an explainable report for an analysis job.

    When ``score`` / ``indicators`` are omitted, the AOI is scored via
    ``ScoreAoiUseCase`` using optional vegetation overrides.
    """

    analysis_job_id: UUID
    score: GreenDeficiencyScore | None = None
    indicators: IndicatorValues | None = None
    vegetation_coverage: float | None = None
    green_area_m2: float | None = None
    park_walk_distance_m: float = 300.0
    aoi_name: str | None = None


class GenerateReportUseCase:
    """Build an explainable report and persist it for an analysis job."""

    def __init__(
        self,
        uow: UnitOfWork,
        explainer: ReportExplainerPort,
        score_aoi: ScoreAoiUseCase | None = None,
    ) -> None:
        self._uow = uow
        self._explainer = explainer
        self._score_aoi = score_aoi

    def execute(self, command: GenerateReportCommand) -> AnalysisReport:
        """Return the persisted report for ``command.analysis_job_id``."""

        job = self._uow.analysis_jobs.get_by_id(command.analysis_job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{command.analysis_job_id}' was not found.")

        aoi = self._uow.areas_of_interest.get_by_id(job.aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{job.aoi_id}' was not found.")

        score = command.score
        indicators = command.indicators
        if score is None or indicators is None:
            if self._score_aoi is None:
                raise ValidationError(
                    "Score and indicators are required when ScoreAoiUseCase is not configured."
                )
            scored = self._score_aoi.execute(
                ScoreAoiCommand(
                    aoi_id=job.aoi_id,
                    scoring_profile_id=job.scoring_profile_id,
                    vegetation_coverage=command.vegetation_coverage,
                    green_area_m2=command.green_area_m2,
                    park_walk_distance_m=command.park_walk_distance_m,
                )
            )
            score = scored.score
            indicators = scored.indicators

        content: ExplainableReportContent = self._explainer.explain(
            score,
            indicators,
            aoi_name=command.aoi_name or aoi.name,
        )
        report = AnalysisReport.from_content(
            analysis_job_id=job.id,
            aoi_id=job.aoi_id,
            scoring_profile_id=job.scoring_profile_id,
            content=content,
        )
        saved = self._uow.analysis_reports.add(report)
        self._uow.commit()
        return saved


class GetReportUseCase:
    """Fetch a single explainable report by id."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, report_id: UUID) -> AnalysisReport:
        report = self._uow.analysis_reports.get_by_id(report_id)
        if report is None:
            raise NotFoundError(f"Analysis report '{report_id}' was not found.")
        return report


class GetReportByJobUseCase:
    """Fetch the explainable report linked to an analysis job."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, job_id: UUID) -> AnalysisReport:
        job = self._uow.analysis_jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError(f"Analysis job '{job_id}' was not found.")
        report = self._uow.analysis_reports.get_by_job_id(job_id)
        if report is None:
            raise NotFoundError(f"No report found for analysis job '{job_id}'.")
        return report
