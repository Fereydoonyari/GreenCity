"""Scoring profile CRUD HTTP endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from greencity.application.use_cases.scoring_profiles import (
    CreateScoringProfileCommand,
    CreateScoringProfileUseCase,
    DeleteScoringProfileUseCase,
    GetScoringProfileUseCase,
    ListScoringProfilesUseCase,
    UpdateScoringProfileCommand,
    UpdateScoringProfileUseCase,
)
from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.presentation.dependencies import (
    CurrentUser,
    provide_create_scoring_profile_use_case,
    provide_delete_scoring_profile_use_case,
    provide_get_scoring_profile_use_case,
    provide_list_scoring_profiles_use_case,
    provide_update_scoring_profile_use_case,
)
from greencity.domain.exceptions import ForbiddenError
from greencity.presentation.schemas.scoring_profiles import (
    IndicatorWeightsSchema,
    ScoringProfileCreateRequest,
    ScoringProfileResponse,
    ScoringProfileUpdateRequest,
)

router = APIRouter(prefix="/scoring-profiles")


def _to_response(profile: ScoringProfile) -> ScoringProfileResponse:
    """Map a domain scoring profile to the HTTP response schema."""

    return ScoringProfileResponse(
        id=profile.id,
        owner_id=profile.owner_id,
        name=profile.name,
        description=profile.description,
        weights=IndicatorWeightsSchema(**profile.weights.as_dict()),
        is_default=profile.is_default,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.post(
    "",
    response_model=ScoringProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create scoring profile",
)
def create_scoring_profile(
    body: ScoringProfileCreateRequest,
    current_user: CurrentUser,
    use_case: Annotated[
        CreateScoringProfileUseCase, Depends(provide_create_scoring_profile_use_case)
    ],
) -> ScoringProfileResponse:
    """Create a configurable Green Deficiency scoring profile for the caller."""

    profile = use_case.execute(
        CreateScoringProfileCommand(
            owner_id=current_user.id,
            name=body.name,
            description=body.description,
            weights=body.weights.model_dump() if body.weights else None,
            is_default=body.is_default,
            use_balanced_defaults=body.use_balanced_defaults,
        )
    )
    return _to_response(profile)


@router.get("", response_model=list[ScoringProfileResponse], summary="List scoring profiles")
def list_scoring_profiles(
    current_user: CurrentUser,
    use_case: Annotated[
        ListScoringProfilesUseCase, Depends(provide_list_scoring_profiles_use_case)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScoringProfileResponse]:
    """Return scoring profiles owned by the authenticated user."""

    profiles = use_case.execute(owner_id=current_user.id, limit=limit, offset=offset)
    return [_to_response(p) for p in profiles]


@router.get(
    "/{profile_id}",
    response_model=ScoringProfileResponse,
    summary="Get scoring profile",
)
def get_scoring_profile(
    profile_id: UUID,
    current_user: CurrentUser,
    use_case: Annotated[GetScoringProfileUseCase, Depends(provide_get_scoring_profile_use_case)],
) -> ScoringProfileResponse:
    """Return a single scoring profile owned by the caller."""

    profile = use_case.execute(profile_id)
    if profile.owner_id != current_user.id:
        raise ForbiddenError("You do not own this scoring profile.")
    return _to_response(profile)


@router.patch(
    "/{profile_id}",
    response_model=ScoringProfileResponse,
    summary="Update scoring profile",
)
def update_scoring_profile(
    profile_id: UUID,
    body: ScoringProfileUpdateRequest,
    current_user: CurrentUser,
    get_use_case: Annotated[
        GetScoringProfileUseCase, Depends(provide_get_scoring_profile_use_case)
    ],
    use_case: Annotated[
        UpdateScoringProfileUseCase, Depends(provide_update_scoring_profile_use_case)
    ],
) -> ScoringProfileResponse:
    """Update mutable scoring profile fields."""

    existing = get_use_case.execute(profile_id)
    if existing.owner_id != current_user.id:
        raise ForbiddenError("You do not own this scoring profile.")
    profile = use_case.execute(
        profile_id,
        UpdateScoringProfileCommand(
            name=body.name,
            description=body.description,
            weights=body.weights.model_dump() if body.weights else None,
            is_default=body.is_default,
        ),
    )
    return _to_response(profile)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete scoring profile",
)
def delete_scoring_profile(
    profile_id: UUID,
    current_user: CurrentUser,
    get_use_case: Annotated[
        GetScoringProfileUseCase, Depends(provide_get_scoring_profile_use_case)
    ],
    use_case: Annotated[
        DeleteScoringProfileUseCase, Depends(provide_delete_scoring_profile_use_case)
    ],
) -> None:
    """Permanently delete a scoring profile."""

    existing = get_use_case.execute(profile_id)
    if existing.owner_id != current_user.id:
        raise ForbiddenError("You do not own this scoring profile.")
    use_case.execute(profile_id)
