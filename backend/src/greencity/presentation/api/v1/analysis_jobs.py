"""Analysis job lifecycle HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from greencity.application.use_cases.analysis_jobs import (
    CancelAnalysisJobUseCase,
    CompleteAnalysisJobUseCase,
    CreateAnalysisJobCommand,
    CreateAnalysisJobUseCase,
    FailAnalysisJobUseCase,
    GetAnalysisJobUseCase,
    ListAnalysisJobsUseCase,
    StartAnalysisJobUseCase,
    UpdateAnalysisJobProgressCommand,
    UpdateAnalysisJobProgressUseCase,
)
from greencity.application.use_cases.orchestration import (
    RunAnalysisOrchestrationCommand,
    RunAnalysisOrchestrationUseCase,
)
from greencity.application.use_cases.reports import GetReportByJobUseCase
from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.value_objects.orchestration import AnalysisOrchestrationResult
from greencity.presentation.dependencies import (
    CurrentUser,
    UnitOfWorkDep,
    provide_cancel_analysis_job_use_case,
    provide_complete_analysis_job_use_case,
    provide_create_analysis_job_use_case,
    provide_fail_analysis_job_use_case,
    provide_get_analysis_job_use_case,
    provide_get_report_by_job_use_case,
    provide_list_analysis_jobs_use_case,
    provide_notify_analysis_complete_use_case,
    provide_run_analysis_orchestration_use_case,
    provide_start_analysis_job_use_case,
    provide_update_analysis_job_progress_use_case,
)
from greencity.application.use_cases.notifications import (
    NotifyAnalysisCompleteCommand,
    NotifyAnalysisCompleteUseCase,
)
from greencity.config import get_settings
from greencity.presentation.ownership import require_owned_project
from greencity.presentation.schemas.analysis_jobs import (
    AnalysisJobCreateRequest,
    AnalysisJobFailRequest,
    AnalysisJobProgressRequest,
    AnalysisJobResponse,
)
from greencity.presentation.schemas.indicators import IndicatorValuesSchema
from greencity.presentation.schemas.orchestration import (
    AnalysisOrchestrationSchema,
    RunAnalysisRequest,
    RunAnalysisResponse,
)
from greencity.presentation.schemas.reports import AnalysisReportResponse
from greencity.presentation.schemas.scoring import (
    GreenDeficiencyScoreSchema,
    IndicatorContributionSchema,
)
router = APIRouter(prefix="/analysis-jobs")


def _to_response(job: AnalysisJob) -> AnalysisJobResponse:
    """Map a domain analysis job to the HTTP response schema."""

    return AnalysisJobResponse.model_validate(job)


@router.post(
    "",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create analysis job",
)
def create_analysis_job(
    body: AnalysisJobCreateRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[CreateAnalysisJobUseCase, Depends(provide_create_analysis_job_use_case)],
) -> AnalysisJobResponse:
    """Queue a new analysis job for a project AOI and scoring profile."""

    require_owned_project(uow, body.project_id, current_user)
    job = use_case.execute(
        CreateAnalysisJobCommand(
            project_id=body.project_id,
            aoi_id=body.aoi_id,
            scoring_profile_id=body.scoring_profile_id,
        )
    )
    return _to_response(job)


@router.get("", response_model=list[AnalysisJobResponse], summary="List analysis jobs")
def list_analysis_jobs(
    project_id: Annotated[UUID, Query(description="Project that owns the jobs")],
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[ListAnalysisJobsUseCase, Depends(provide_list_analysis_jobs_use_case)],
    status_filter: Annotated[
        AnalysisJobStatus | None,
        Query(alias="status", description="Optional status filter"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AnalysisJobResponse]:
    """Return analysis jobs for an owned project."""

    require_owned_project(uow, project_id, current_user)
    jobs = use_case.execute(
        project_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return [_to_response(j) for j in jobs]


@router.get("/{job_id}", response_model=AnalysisJobResponse, summary="Get analysis job")
def get_analysis_job(
    job_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
) -> AnalysisJobResponse:
    """Return a single analysis job by id."""

    job = use_case.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    return _to_response(job)


@router.post("/{job_id}/start", response_model=AnalysisJobResponse, summary="Start analysis job")
def start_analysis_job(
    job_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_use_case: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
    use_case: Annotated[StartAnalysisJobUseCase, Depends(provide_start_analysis_job_use_case)],
) -> AnalysisJobResponse:
    """Transition a queued job to running."""

    job = get_use_case.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    return _to_response(use_case.execute(job_id))


def _analysis_schema(result: AnalysisOrchestrationResult) -> AnalysisOrchestrationSchema:
    gds = result.score
    report_schema = (
        AnalysisReportResponse.model_validate(result.report) if result.report is not None else None
    )
    return AnalysisOrchestrationSchema(
        aoi_id=result.aoi_id,
        scoring_profile_id=result.scoring_profile_id,
        indicators=IndicatorValuesSchema(**result.indicators.as_dict()),
        green_deficiency_score=GreenDeficiencyScoreSchema(
            score=gds.score,
            priority_band=gds.priority_band,
            normalisation=gds.normalisation,
            contributions=[
                IndicatorContributionSchema(
                    key=c.key,
                    raw_value=c.raw_value,
                    normalised=c.normalised,
                    deficiency_component=c.deficiency_component,
                    weight=c.weight,
                    weighted_contribution=c.weighted_contribution,
                    direction=c.direction.value,
                )
                for c in gds.contributions
            ],
        ),
        steps_completed=list(result.steps_completed),
        summary=result.summary,
        vegetation_source=result.vegetation_source,
        green_area_source=result.green_area_source,
        report=report_schema,
        vegetation_mask=result.vegetation_mask,
        vegetation_hotspot_mask=result.vegetation_hotspot_mask,
        park_access_mask=result.park_access_mask,
        heat_exposure_mask=result.heat_exposure_mask,
        mean_nearest_park_distance_m=result.mean_nearest_park_distance_m,
        median_nearest_park_distance_m=result.median_nearest_park_distance_m,
        mean_nearest_park_walk_min=result.mean_nearest_park_walk_min,
        median_nearest_park_walk_min=result.median_nearest_park_walk_min,
        mean_lst_c=result.mean_lst_c,
        heat_source=result.heat_source,
    )


@router.get(
    "/{job_id}/report",
    response_model=AnalysisReportResponse,
    summary="Get explainable report for an analysis job",
)
def get_analysis_job_report(
    job_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_job: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
    use_case: Annotated[GetReportByJobUseCase, Depends(provide_get_report_by_job_use_case)],
) -> AnalysisReportResponse:
    """Return the explainable report linked to an analysis job."""

    job = get_job.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    return AnalysisReportResponse.model_validate(use_case.execute(job_id))


@router.post(
    "/{job_id}/run",
    response_model=RunAnalysisResponse,
    summary="Run LangGraph analysis orchestration for a job",
)
def run_analysis_job(
    job_id: UUID,
    body: RunAnalysisRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_job: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
    use_case: Annotated[
        RunAnalysisOrchestrationUseCase,
        Depends(provide_run_analysis_orchestration_use_case),
    ],
    notify: Annotated[
        NotifyAnalysisCompleteUseCase,
        Depends(provide_notify_analysis_complete_use_case),
    ],
) -> RunAnalysisResponse:
    """Start (optional) and orchestrate the full analysis graph for a job.

    Steps: validate → indicators (OSM) → GDS score → explainable report.
    On success, emails a template summary to the project owner (logged when SMTP is off).
    """

    job = get_job.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    result = use_case.execute(
        RunAnalysisOrchestrationCommand(
            job_id=job_id,
            vegetation_coverage=body.vegetation_coverage,
            green_area_m2=body.green_area_m2,
            park_walk_distance_m=body.park_walk_distance_m,
            auto_start=body.auto_start,
        )
    )
    if get_settings().email_on_analysis_complete and result.analysis.report is not None:
        try:
            notify.execute(
                NotifyAnalysisCompleteCommand(
                    project_id=result.job.project_id,
                    aoi_id=result.job.aoi_id,
                    analysis_job_id=result.job.id,
                    owner_id=current_user.id,
                )
            )
        except Exception:  # noqa: BLE001 — email must not fail the analysis response
            pass
    return RunAnalysisResponse(
        job=_to_response(result.job),
        analysis=_analysis_schema(result.analysis),
    )


@router.post("/{job_id}/cancel", response_model=AnalysisJobResponse, summary="Cancel analysis job")
def cancel_analysis_job(
    job_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_job: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
    use_case: Annotated[CancelAnalysisJobUseCase, Depends(provide_cancel_analysis_job_use_case)],
) -> AnalysisJobResponse:
    """Cancel a queued or running job."""

    job = get_job.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    return _to_response(use_case.execute(job_id))


@router.patch(
    "/{job_id}/progress",
    response_model=AnalysisJobResponse,
    summary="Update analysis job progress",
)
def update_analysis_job_progress(
    job_id: UUID,
    body: AnalysisJobProgressRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_job: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
    use_case: Annotated[
        UpdateAnalysisJobProgressUseCase,
        Depends(provide_update_analysis_job_progress_use_case),
    ],
) -> AnalysisJobResponse:
    """Update step/progress while a job is running (worker/agent hook)."""

    job = get_job.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    return _to_response(
        use_case.execute(
            job_id,
            UpdateAnalysisJobProgressCommand(
                current_step=body.current_step,
                progress_pct=body.progress_pct,
            ),
        )
    )


@router.post(
    "/{job_id}/complete",
    response_model=AnalysisJobResponse,
    summary="Complete analysis job",
)
def complete_analysis_job(
    job_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_job: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
    use_case: Annotated[
        CompleteAnalysisJobUseCase, Depends(provide_complete_analysis_job_use_case)
    ],
) -> AnalysisJobResponse:
    """Mark a running job as completed."""

    job = get_job.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    return _to_response(use_case.execute(job_id))


@router.post("/{job_id}/fail", response_model=AnalysisJobResponse, summary="Fail analysis job")
def fail_analysis_job(
    job_id: UUID,
    body: AnalysisJobFailRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_job: Annotated[GetAnalysisJobUseCase, Depends(provide_get_analysis_job_use_case)],
    use_case: Annotated[FailAnalysisJobUseCase, Depends(provide_fail_analysis_job_use_case)],
) -> AnalysisJobResponse:
    """Mark a job as failed with an error message."""

    job = get_job.execute(job_id)
    require_owned_project(uow, job.project_id, current_user)
    return _to_response(use_case.execute(job_id, body.message))
