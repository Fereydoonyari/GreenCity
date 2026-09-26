"""Health endpoint – readiness probe for the API and database."""

from fastapi import APIRouter, Depends

from greencity.application.use_cases.check_health import CheckHealthUseCase
from greencity.presentation.dependencies import provide_check_health_use_case
from greencity.presentation.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description="Returns overall readiness including database connectivity.",
)
def get_health(
    use_case: CheckHealthUseCase = Depends(provide_check_health_use_case),
) -> HealthResponse:
    """Execute the health-check use case and map the result to HTTP."""

    result = use_case.execute()
    return HealthResponse(
        status=result.status,
        database=result.database,
        version=result.version,
    )
