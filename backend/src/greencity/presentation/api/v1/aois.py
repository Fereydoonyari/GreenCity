"""Area of Interest CRUD HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from greencity.application.use_cases.aois import (
    CreateAreaOfInterestCommand,
    CreateAreaOfInterestUseCase,
    DeleteAreaOfInterestUseCase,
    GetAreaOfInterestUseCase,
    ListAreasOfInterestUseCase,
    UpdateAreaOfInterestCommand,
    UpdateAreaOfInterestUseCase,
)
from greencity.domain.entities.aoi import AreaOfInterest
from greencity.presentation.dependencies import (
    CurrentUser,
    UnitOfWorkDep,
    provide_create_aoi_use_case,
    provide_delete_aoi_use_case,
    provide_get_aoi_use_case,
    provide_list_aois_use_case,
    provide_update_aoi_use_case,
)
from greencity.presentation.ownership import require_owned_project
from greencity.presentation.schemas.aois import (
    AreaOfInterestCreateRequest,
    AreaOfInterestResponse,
    AreaOfInterestUpdateRequest,
)

router = APIRouter(prefix="/areas-of-interest")


def _to_response(aoi: AreaOfInterest) -> AreaOfInterestResponse:
    """Map a domain AOI to the HTTP response schema."""

    return AreaOfInterestResponse(
        id=aoi.id,
        project_id=aoi.project_id,
        name=aoi.name,
        description=aoi.description,
        kind=aoi.kind,
        parent_aoi_id=aoi.parent_aoi_id,
        geometry=aoi.geometry.data,
        created_at=aoi.created_at,
        updated_at=aoi.updated_at,
    )


@router.post(
    "",
    response_model=AreaOfInterestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create area of interest",
)
def create_aoi(
    body: AreaOfInterestCreateRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[CreateAreaOfInterestUseCase, Depends(provide_create_aoi_use_case)],
) -> AreaOfInterestResponse:
    """Create an AOI from GeoJSON geometry for an owned project."""

    require_owned_project(uow, body.project_id, current_user)
    aoi = use_case.execute(
        CreateAreaOfInterestCommand(
            project_id=body.project_id,
            name=body.name,
            description=body.description,
            geometry=body.geometry,
            kind=body.kind,
            parent_aoi_id=body.parent_aoi_id,
        )
    )
    return _to_response(aoi)


@router.get("", response_model=list[AreaOfInterestResponse], summary="List AOIs for a project")
def list_aois(
    project_id: Annotated[UUID, Query(description="Project that owns the AOIs")],
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[ListAreasOfInterestUseCase, Depends(provide_list_aois_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AreaOfInterestResponse]:
    """Return AOIs belonging to an owned ``project_id``."""

    require_owned_project(uow, project_id, current_user)
    aois = use_case.execute(project_id, limit=limit, offset=offset)
    return [_to_response(a) for a in aois]


@router.get("/{aoi_id}", response_model=AreaOfInterestResponse, summary="Get AOI")
def get_aoi(
    aoi_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[GetAreaOfInterestUseCase, Depends(provide_get_aoi_use_case)],
) -> AreaOfInterestResponse:
    """Return a single AOI by id when the caller owns its project."""

    aoi = use_case.execute(aoi_id)
    require_owned_project(uow, aoi.project_id, current_user)
    return _to_response(aoi)


@router.patch("/{aoi_id}", response_model=AreaOfInterestResponse, summary="Update AOI")
def update_aoi(
    aoi_id: UUID,
    body: AreaOfInterestUpdateRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_use_case: Annotated[GetAreaOfInterestUseCase, Depends(provide_get_aoi_use_case)],
    use_case: Annotated[UpdateAreaOfInterestUseCase, Depends(provide_update_aoi_use_case)],
) -> AreaOfInterestResponse:
    """Update mutable AOI fields / geometry on an owned project."""

    existing = get_use_case.execute(aoi_id)
    require_owned_project(uow, existing.project_id, current_user)
    aoi = use_case.execute(
        aoi_id,
        UpdateAreaOfInterestCommand(
            name=body.name,
            description=body.description,
            geometry=body.geometry,
        ),
    )
    return _to_response(aoi)


@router.delete(
    "/{aoi_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete AOI",
)
def delete_aoi(
    aoi_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    get_use_case: Annotated[GetAreaOfInterestUseCase, Depends(provide_get_aoi_use_case)],
    use_case: Annotated[DeleteAreaOfInterestUseCase, Depends(provide_delete_aoi_use_case)],
) -> None:
    """Permanently delete an AOI on an owned project."""

    existing = get_use_case.execute(aoi_id)
    require_owned_project(uow, existing.project_id, current_user)
    use_case.execute(aoi_id)
