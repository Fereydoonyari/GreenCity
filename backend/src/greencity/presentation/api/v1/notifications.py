"""Notification HTTP endpoints (analysis summary emails)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from greencity.application.use_cases.notifications import (
    NotifyComparisonSummaryCommand,
    NotifyComparisonSummaryUseCase,
    RankingLine,
)
from greencity.presentation.dependencies import (
    CurrentUser,
    provide_notify_comparison_summary_use_case,
)

router = APIRouter(prefix="/notifications")


class RankingLineSchema(BaseModel):
    """One ranked neighborhood for the comparison email."""

    rank: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=200)
    score: float
    priority_band: str


class ComparisonSummaryRequest(BaseModel):
    """Body for ``POST /notifications/comparison-summary``."""

    project_id: UUID
    rankings: list[RankingLineSchema] = Field(min_length=1)
    notes: str = Field(default="", max_length=5000)


@router.post(
    "/comparison-summary",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Email neighborhood comparison summary to the project owner",
)
def send_comparison_summary(
    body: ComparisonSummaryRequest,
    current_user: CurrentUser,
    use_case: Annotated[
        NotifyComparisonSummaryUseCase,
        Depends(provide_notify_comparison_summary_use_case),
    ],
) -> None:
    """Send a template comparison digest to the authenticated project owner."""

    use_case.execute(
        NotifyComparisonSummaryCommand(
            project_id=body.project_id,
            owner_id=current_user.id,
            rankings=tuple(
                RankingLine(
                    rank=row.rank,
                    name=row.name,
                    score=row.score,
                    priority_band=row.priority_band,
                )
                for row in body.rankings
            ),
            notes=body.notes,
        )
    )
