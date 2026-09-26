"""User CRUD HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from greencity.application.use_cases.users import (
    CreateUserCommand,
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    UpdateUserCommand,
    UpdateUserUseCase,
)
from greencity.presentation.dependencies import (
    provide_create_user_use_case,
    provide_delete_user_use_case,
    provide_get_user_use_case,
    provide_list_users_use_case,
    provide_update_user_use_case,
)
from greencity.presentation.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users")


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
def create_user(
    body: UserCreateRequest,
    use_case: Annotated[CreateUserUseCase, Depends(provide_create_user_use_case)],
) -> UserResponse:
    """Register a new user account."""

    user = use_case.execute(
        CreateUserCommand(
            email=str(body.email),
            full_name=body.full_name,
            password=body.password,
        )
    )
    return UserResponse.model_validate(user)


@router.get("", response_model=list[UserResponse], summary="List users")
def list_users(
    use_case: Annotated[ListUsersUseCase, Depends(provide_list_users_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserResponse]:
    """Return a paginated list of users."""

    users = use_case.execute(limit=limit, offset=offset)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse, summary="Get user")
def get_user(
    user_id: UUID,
    use_case: Annotated[GetUserUseCase, Depends(provide_get_user_use_case)],
) -> UserResponse:
    """Return a single user by id."""

    return UserResponse.model_validate(use_case.execute(user_id))


@router.patch("/{user_id}", response_model=UserResponse, summary="Update user")
def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    use_case: Annotated[UpdateUserUseCase, Depends(provide_update_user_use_case)],
) -> UserResponse:
    """Update mutable user fields."""

    user = use_case.execute(
        user_id,
        UpdateUserCommand(full_name=body.full_name, is_active=body.is_active),
    )
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
)
def delete_user(
    user_id: UUID,
    use_case: Annotated[DeleteUserUseCase, Depends(provide_delete_user_use_case)],
) -> None:
    """Permanently delete a user and cascaded projects."""

    use_case.execute(user_id)
