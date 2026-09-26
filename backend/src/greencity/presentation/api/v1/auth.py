"""Authentication HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from greencity.application.use_cases.auth import (
    LoginCommand,
    LoginUserUseCase,
    RegisterUserUseCase,
)
from greencity.application.use_cases.users import CreateUserCommand
from greencity.presentation.dependencies import (
    CurrentUser,
    provide_login_user_use_case,
    provide_register_user_use_case,
)
from greencity.presentation.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from greencity.presentation.schemas.users import UserResponse

router = APIRouter(prefix="/auth")


def _token_response(result: object) -> TokenResponse:
    return TokenResponse(
        access_token=result.access_token,  # type: ignore[attr-defined]
        token_type=result.token_type,  # type: ignore[attr-defined]
        user=UserResponse.model_validate(result.user),  # type: ignore[attr-defined]
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register with email and password",
)
def register(
    body: RegisterRequest,
    use_case: Annotated[RegisterUserUseCase, Depends(provide_register_user_use_case)],
) -> TokenResponse:
    """Create an account and return an access token."""

    result = use_case.execute(
        CreateUserCommand(
            email=str(body.email),
            full_name=body.full_name,
            password=body.password,
        )
    )
    return _token_response(result)


@router.post("/login", response_model=TokenResponse, summary="Login with email and password")
def login(
    body: LoginRequest,
    use_case: Annotated[LoginUserUseCase, Depends(provide_login_user_use_case)],
) -> TokenResponse:
    """Authenticate and return an access token."""

    result = use_case.execute(
        LoginCommand(email=str(body.email), password=body.password)
    )
    return _token_response(result)


@router.get("/me", response_model=UserResponse, summary="Current user profile")
def me(current_user: CurrentUser) -> UserResponse:
    """Return the authenticated user."""

    return UserResponse.model_validate(current_user)
