"""Project CRUD HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from greencity.application.use_cases.projects import (
    CreateProjectCommand,
    CreateProjectUseCase,
    DeleteProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
    UpdateProjectCommand,
    UpdateProjectUseCase,
)
from greencity.presentation.dependencies import (
    CurrentUser,
    UnitOfWorkDep,
    provide_create_project_use_case,
    provide_delete_project_use_case,
    provide_get_project_use_case,
    provide_list_projects_use_case,
    provide_update_project_use_case,
)
from greencity.presentation.ownership import require_owned_project
from greencity.presentation.schemas.projects import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)

router = APIRouter(prefix="/projects")


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
)
def create_project(
    body: ProjectCreateRequest,
    current_user: CurrentUser,
    use_case: Annotated[CreateProjectUseCase, Depends(provide_create_project_use_case)],
) -> ProjectResponse:
    """Create a planning project owned by the authenticated user."""

    project = use_case.execute(
        CreateProjectCommand(
            name=body.name,
            description=body.description,
            owner_id=current_user.id,
            status=body.status,
        )
    )
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse], summary="List my projects")
def list_projects(
    current_user: CurrentUser,
    use_case: Annotated[ListProjectsUseCase, Depends(provide_list_projects_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProjectResponse]:
    """Return projects owned by the authenticated user."""

    projects = use_case.execute(owner_id=current_user.id, limit=limit, offset=offset)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project")
def get_project(
    project_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> ProjectResponse:
    """Return a single owned project by id."""

    project = require_owned_project(uow, project_id, current_user)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse, summary="Update project")
def update_project(
    project_id: UUID,
    body: ProjectUpdateRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[UpdateProjectUseCase, Depends(provide_update_project_use_case)],
) -> ProjectResponse:
    """Update mutable fields on an owned project."""

    require_owned_project(uow, project_id, current_user)
    project = use_case.execute(
        project_id,
        UpdateProjectCommand(
            name=body.name,
            description=body.description,
            status=body.status,
        ),
    )
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
)
def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    use_case: Annotated[DeleteProjectUseCase, Depends(provide_delete_project_use_case)],
) -> None:
    """Permanently delete an owned project."""

    require_owned_project(uow, project_id, current_user)
    use_case.execute(project_id)
