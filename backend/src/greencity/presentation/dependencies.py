"""API dependency providers for FastAPI routes."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from greencity.application.use_cases.agent_narratives import (
    GenerateNeighborhoodBriefUseCase,
    GenerateNeighborhoodComparisonUseCase,
    GenerateVegetationPlanUseCase,
)
from greencity.application.use_cases.analysis_jobs import (
    CancelAnalysisJobUseCase,
    CompleteAnalysisJobUseCase,
    CreateAnalysisJobUseCase,
    FailAnalysisJobUseCase,
    GetAnalysisJobUseCase,
    ListAnalysisJobsUseCase,
    StartAnalysisJobUseCase,
    UpdateAnalysisJobProgressUseCase,
)
from greencity.application.use_cases.aois import (
    CreateAreaOfInterestUseCase,
    DeleteAreaOfInterestUseCase,
    GetAreaOfInterestUseCase,
    ListAreasOfInterestUseCase,
    UpdateAreaOfInterestUseCase,
)
from greencity.application.use_cases.auth import (
    LoginUserUseCase,
    RegisterUserUseCase,
    ResolveCurrentUserUseCase,
)
from greencity.application.use_cases.check_health import CheckHealthUseCase
from greencity.application.use_cases.indicators import ComputeIndicatorsUseCase
from greencity.application.use_cases.notifications import (
    NotifyAnalysisCompleteUseCase,
    NotifyComparisonSummaryUseCase,
)
from greencity.application.use_cases.orchestration import RunAnalysisOrchestrationUseCase
from greencity.application.use_cases.projects import (
    CreateProjectUseCase,
    DeleteProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
    UpdateProjectUseCase,
)
from greencity.application.use_cases.reports import (
    GenerateReportUseCase,
    GetReportByJobUseCase,
    GetReportUseCase,
)
from greencity.application.use_cases.scoring import RankNeighborhoodsUseCase, ScoreAoiUseCase
from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileUseCase,
    DeleteScoringProfileUseCase,
    GetScoringProfileUseCase,
    ListScoringProfilesUseCase,
    UpdateScoringProfileUseCase,
)
from greencity.application.use_cases.urban_context import FetchOsmContextUseCase
from greencity.application.use_cases.users import (
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserUseCase,
)
from greencity.config import get_settings
from greencity.domain.entities.user import User
from greencity.domain.exceptions import UnauthorizedError
from greencity.infrastructure.agent import LangGraphAnalysisOrchestrator
from greencity.infrastructure.agent.narratives import build_neighborhood_agent_narrator
from greencity.infrastructure.di import get_check_health_use_case, get_session_factory
from greencity.infrastructure.imagery import HlsEarthAccessAdapter, NumpyVegetationPipeline
from greencity.infrastructure.imagery.landsat import LandsatThermalAdapter
from greencity.infrastructure.indicators import BufferParkAccessibility
from greencity.infrastructure.notifications import build_email_notifier
from greencity.infrastructure.osm import OverpassOsmAdapter
from greencity.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from greencity.infrastructure.reporting import build_report_explainer
from greencity.infrastructure.security.password_hasher import BcryptPasswordHasher
from greencity.infrastructure.security.tokens import JwtAccessTokenService

_bearer_scheme = HTTPBearer(auto_error=False)


def _token_service() -> JwtAccessTokenService:
    settings = get_settings()
    return JwtAccessTokenService(
        secret=settings.jwt_secret,
        expire_minutes=settings.jwt_expire_minutes,
    )


def _osm_adapter() -> OverpassOsmAdapter:
    """Build Overpass adapter from settings (mirrors, cache, soft-fail)."""

    settings = get_settings()
    return OverpassOsmAdapter(
        overpass_url=settings.overpass_url,
        mirror_urls=tuple(settings.overpass_mirror_urls),
        timeout_s=settings.overpass_timeout_s,
        retries_per_mirror=settings.overpass_retries_per_mirror,
        cache_ttl_s=settings.overpass_cache_ttl_s,
        cache_dir=settings.overpass_cache_dir,
        soft_fail=True,
    )


def _hls_ports() -> tuple[HlsEarthAccessAdapter | None, NumpyVegetationPipeline | None]:
    """Return HLS imagery + NDVI pipeline when credentials enable acquisition."""

    settings = get_settings()
    if not settings.hls_acquisition_enabled:
        return None, None
    return HlsEarthAccessAdapter(settings), NumpyVegetationPipeline()


def _thermal_port() -> LandsatThermalAdapter | None:
    """Return Landsat ST adapter when credentials enable acquisition."""

    settings = get_settings()
    if not settings.landsat_acquisition_enabled:
        return None
    return LandsatThermalAdapter(settings)


def provide_check_health_use_case() -> CheckHealthUseCase:
    """FastAPI dependency that resolves the health-check use case."""

    return get_check_health_use_case()


def provide_unit_of_work() -> Generator[SqlAlchemyUnitOfWork, None, None]:
    """Yield a request-scoped SQLAlchemy unit of work."""

    uow = SqlAlchemyUnitOfWork(get_session_factory())
    with uow:
        yield uow


UnitOfWorkDep = Annotated[SqlAlchemyUnitOfWork, Depends(provide_unit_of_work)]


def provide_create_user_use_case(uow: UnitOfWorkDep) -> CreateUserUseCase:
    """Build ``CreateUserUseCase`` for the current request."""

    return CreateUserUseCase(uow, BcryptPasswordHasher())


def provide_register_user_use_case(uow: UnitOfWorkDep) -> RegisterUserUseCase:
    """Build register use case (create user + JWT)."""

    return RegisterUserUseCase(provide_create_user_use_case(uow), _token_service())


def provide_login_user_use_case(uow: UnitOfWorkDep) -> LoginUserUseCase:
    """Build login use case."""

    return LoginUserUseCase(uow, BcryptPasswordHasher(), _token_service())


def provide_current_user(
    uow: UnitOfWorkDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ] = None,
) -> User:
    """Resolve the authenticated user from a Bearer access token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Authentication required.")
    user_id = _token_service().parse_user_id(credentials.credentials)
    return ResolveCurrentUserUseCase(uow).execute(user_id)


CurrentUser = Annotated[User, Depends(provide_current_user)]


def provide_get_user_use_case(uow: UnitOfWorkDep) -> GetUserUseCase:
    """Build ``GetUserUseCase`` for the current request."""

    return GetUserUseCase(uow)


def provide_list_users_use_case(uow: UnitOfWorkDep) -> ListUsersUseCase:
    """Build ``ListUsersUseCase`` for the current request."""

    return ListUsersUseCase(uow)


def provide_update_user_use_case(uow: UnitOfWorkDep) -> UpdateUserUseCase:
    """Build ``UpdateUserUseCase`` for the current request."""

    return UpdateUserUseCase(uow)


def provide_delete_user_use_case(uow: UnitOfWorkDep) -> DeleteUserUseCase:
    """Build ``DeleteUserUseCase`` for the current request."""

    return DeleteUserUseCase(uow)


def provide_create_project_use_case(uow: UnitOfWorkDep) -> CreateProjectUseCase:
    """Build ``CreateProjectUseCase`` for the current request."""

    return CreateProjectUseCase(uow)


def provide_get_project_use_case(uow: UnitOfWorkDep) -> GetProjectUseCase:
    """Build ``GetProjectUseCase`` for the current request."""

    return GetProjectUseCase(uow)


def provide_list_projects_use_case(uow: UnitOfWorkDep) -> ListProjectsUseCase:
    """Build ``ListProjectsUseCase`` for the current request."""

    return ListProjectsUseCase(uow)


def provide_update_project_use_case(uow: UnitOfWorkDep) -> UpdateProjectUseCase:
    """Build ``UpdateProjectUseCase`` for the current request."""

    return UpdateProjectUseCase(uow)


def provide_delete_project_use_case(uow: UnitOfWorkDep) -> DeleteProjectUseCase:
    """Build ``DeleteProjectUseCase`` for the current request."""

    return DeleteProjectUseCase(uow)


def provide_create_aoi_use_case(uow: UnitOfWorkDep) -> CreateAreaOfInterestUseCase:
    """Build ``CreateAreaOfInterestUseCase`` for the current request."""

    return CreateAreaOfInterestUseCase(uow)


def provide_get_aoi_use_case(uow: UnitOfWorkDep) -> GetAreaOfInterestUseCase:
    """Build ``GetAreaOfInterestUseCase`` for the current request."""

    return GetAreaOfInterestUseCase(uow)


def provide_list_aois_use_case(uow: UnitOfWorkDep) -> ListAreasOfInterestUseCase:
    """Build ``ListAreasOfInterestUseCase`` for the current request."""

    return ListAreasOfInterestUseCase(uow)


def provide_update_aoi_use_case(uow: UnitOfWorkDep) -> UpdateAreaOfInterestUseCase:
    """Build ``UpdateAreaOfInterestUseCase`` for the current request."""

    return UpdateAreaOfInterestUseCase(uow)


def provide_delete_aoi_use_case(uow: UnitOfWorkDep) -> DeleteAreaOfInterestUseCase:
    """Build ``DeleteAreaOfInterestUseCase`` for the current request."""

    return DeleteAreaOfInterestUseCase(uow)


def provide_create_scoring_profile_use_case(
    uow: UnitOfWorkDep,
) -> CreateScoringProfileUseCase:
    """Build ``CreateScoringProfileUseCase`` for the current request."""

    return CreateScoringProfileUseCase(uow)


def provide_get_scoring_profile_use_case(uow: UnitOfWorkDep) -> GetScoringProfileUseCase:
    """Build ``GetScoringProfileUseCase`` for the current request."""

    return GetScoringProfileUseCase(uow)


def provide_list_scoring_profiles_use_case(
    uow: UnitOfWorkDep,
) -> ListScoringProfilesUseCase:
    """Build ``ListScoringProfilesUseCase`` for the current request."""

    return ListScoringProfilesUseCase(uow)


def provide_update_scoring_profile_use_case(
    uow: UnitOfWorkDep,
) -> UpdateScoringProfileUseCase:
    """Build ``UpdateScoringProfileUseCase`` for the current request."""

    return UpdateScoringProfileUseCase(uow)


def provide_delete_scoring_profile_use_case(
    uow: UnitOfWorkDep,
) -> DeleteScoringProfileUseCase:
    """Build ``DeleteScoringProfileUseCase`` for the current request."""

    return DeleteScoringProfileUseCase(uow)


def provide_create_analysis_job_use_case(uow: UnitOfWorkDep) -> CreateAnalysisJobUseCase:
    """Build ``CreateAnalysisJobUseCase`` for the current request."""

    return CreateAnalysisJobUseCase(uow)


def provide_get_analysis_job_use_case(uow: UnitOfWorkDep) -> GetAnalysisJobUseCase:
    """Build ``GetAnalysisJobUseCase`` for the current request."""

    return GetAnalysisJobUseCase(uow)


def provide_list_analysis_jobs_use_case(uow: UnitOfWorkDep) -> ListAnalysisJobsUseCase:
    """Build ``ListAnalysisJobsUseCase`` for the current request."""

    return ListAnalysisJobsUseCase(uow)


def provide_start_analysis_job_use_case(uow: UnitOfWorkDep) -> StartAnalysisJobUseCase:
    """Build ``StartAnalysisJobUseCase`` for the current request."""

    return StartAnalysisJobUseCase(uow)


def provide_cancel_analysis_job_use_case(uow: UnitOfWorkDep) -> CancelAnalysisJobUseCase:
    """Build ``CancelAnalysisJobUseCase`` for the current request."""

    return CancelAnalysisJobUseCase(uow)


def provide_update_analysis_job_progress_use_case(
    uow: UnitOfWorkDep,
) -> UpdateAnalysisJobProgressUseCase:
    """Build ``UpdateAnalysisJobProgressUseCase`` for the current request."""

    return UpdateAnalysisJobProgressUseCase(uow)


def provide_complete_analysis_job_use_case(
    uow: UnitOfWorkDep,
) -> CompleteAnalysisJobUseCase:
    """Build ``CompleteAnalysisJobUseCase`` for the current request."""

    return CompleteAnalysisJobUseCase(uow)


def provide_fail_analysis_job_use_case(uow: UnitOfWorkDep) -> FailAnalysisJobUseCase:
    """Build ``FailAnalysisJobUseCase`` for the current request."""

    return FailAnalysisJobUseCase(uow)


def provide_fetch_osm_context_use_case(uow: UnitOfWorkDep) -> FetchOsmContextUseCase:
    """Build ``FetchOsmContextUseCase`` with the Overpass OSM adapter."""

    return FetchOsmContextUseCase(uow, _osm_adapter())


def provide_compute_indicators_use_case(uow: UnitOfWorkDep) -> ComputeIndicatorsUseCase:
    """Build ``ComputeIndicatorsUseCase`` with OSM, park, and optional HLS/ST."""

    imagery, pipeline = _hls_ports()
    return ComputeIndicatorsUseCase(
        uow,
        _osm_adapter(),
        BufferParkAccessibility(),
        imagery=imagery,
        vegetation_pipeline=pipeline,
        thermal=_thermal_port(),
    )


def provide_score_aoi_use_case(uow: UnitOfWorkDep) -> ScoreAoiUseCase:
    """Build ``ScoreAoiUseCase`` wired to indicator computation."""

    return ScoreAoiUseCase(uow, provide_compute_indicators_use_case(uow))


def provide_rank_neighborhoods_use_case(uow: UnitOfWorkDep) -> RankNeighborhoodsUseCase:
    """Build ``RankNeighborhoodsUseCase`` for the current request."""

    return RankNeighborhoodsUseCase(uow)


def provide_run_analysis_orchestration_use_case(
    uow: UnitOfWorkDep,
) -> RunAnalysisOrchestrationUseCase:
    """Build orchestration use case with LangGraph + OSM/HLS/ST adapters."""

    imagery, pipeline = _hls_ports()
    orchestrator = LangGraphAnalysisOrchestrator(
        uow,
        _osm_adapter(),
        BufferParkAccessibility(),
        build_report_explainer(),
        imagery=imagery,
        vegetation_pipeline=pipeline,
        thermal=_thermal_port(),
    )
    return RunAnalysisOrchestrationUseCase(uow, orchestrator)


def provide_notify_analysis_complete_use_case(
    uow: UnitOfWorkDep,
) -> NotifyAnalysisCompleteUseCase:
    """Build per-AOI analysis email notifier."""

    return NotifyAnalysisCompleteUseCase(uow, build_email_notifier())


def provide_notify_comparison_summary_use_case(
    uow: UnitOfWorkDep,
) -> NotifyComparisonSummaryUseCase:
    """Build neighborhood comparison email notifier."""

    return NotifyComparisonSummaryUseCase(uow, build_email_notifier())


def provide_generate_neighborhood_brief_use_case(
    uow: UnitOfWorkDep,
) -> GenerateNeighborhoodBriefUseCase:
    """Build comprehensive single-neighborhood agent brief use case."""

    return GenerateNeighborhoodBriefUseCase(uow, build_neighborhood_agent_narrator())


def provide_generate_neighborhood_comparison_use_case(
    uow: UnitOfWorkDep,
) -> GenerateNeighborhoodComparisonUseCase:
    """Build all-neighborhoods agent comparison use case."""

    return GenerateNeighborhoodComparisonUseCase(uow, build_neighborhood_agent_narrator())


def provide_generate_vegetation_plan_use_case(
    uow: UnitOfWorkDep,
) -> GenerateVegetationPlanUseCase:
    """Build geo-aware vegetation planting plan use case."""

    return GenerateVegetationPlanUseCase(uow, build_neighborhood_agent_narrator())


def provide_generate_report_use_case(uow: UnitOfWorkDep) -> GenerateReportUseCase:
    """Build ``GenerateReportUseCase`` with scoring + report explainer."""

    return GenerateReportUseCase(
        uow,
        build_report_explainer(),
        provide_score_aoi_use_case(uow),
    )


def provide_get_report_use_case(uow: UnitOfWorkDep) -> GetReportUseCase:
    """Build ``GetReportUseCase`` for the current request."""

    return GetReportUseCase(uow)


def provide_get_report_by_job_use_case(uow: UnitOfWorkDep) -> GetReportByJobUseCase:
    """Build ``GetReportByJobUseCase`` for the current request."""

    return GetReportByJobUseCase(uow)
