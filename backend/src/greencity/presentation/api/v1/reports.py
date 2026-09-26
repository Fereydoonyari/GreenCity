"""Explainable analysis report HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from greencity.application.use_cases.reports import (
    GenerateReportCommand,
    GenerateReportUseCase,
    GetReportByJobUseCase,
    GetReportUseCase,
)
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.presentation.dependencies import (
    provide_generate_report_use_case,
    provide_get_report_by_job_use_case,
    provide_get_report_use_case,
)
from greencity.presentation.schemas.reports import (
    AnalysisReportResponse,
    GenerateReportRequest,
)

router = APIRouter(prefix="/reports")


def _to_response(report: AnalysisReport) -> AnalysisReportResponse:
    return AnalysisReportResponse.model_validate(report)


@router.post(
    "",
    response_model=AnalysisReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate explainable report for an analysis job",
)
def generate_report(
    body: GenerateReportRequest,
    use_case: Annotated[GenerateReportUseCase, Depends(provide_generate_report_use_case)],
) -> AnalysisReportResponse:
    """Score the job's AOI (if needed) and persist an explainable report."""

    report = use_case.execute(
        GenerateReportCommand(
            analysis_job_id=body.analysis_job_id,
            vegetation_coverage=body.vegetation_coverage,
            green_area_m2=body.green_area_m2,
            park_walk_distance_m=body.park_walk_distance_m,
            aoi_name=body.aoi_name,
        )
    )
    return _to_response(report)


@router.get("/{report_id}", response_model=AnalysisReportResponse, summary="Get report")
def get_report(
    report_id: UUID,
    use_case: Annotated[GetReportUseCase, Depends(provide_get_report_use_case)],
) -> AnalysisReportResponse:
    """Return a single explainable report by id."""

    return _to_response(use_case.execute(report_id))
