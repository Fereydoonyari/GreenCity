"""Send analysis / comparison summary emails to project owners."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from greencity.domain.ports.notifications import EmailNotifier
from greencity.domain.ports.repositories import UnitOfWork
from greencity.infrastructure.notifications.email import (
    render_analysis_summary_email,
    render_comparison_summary_email,
)


@dataclass(frozen=True)
class NotifyAnalysisCompleteCommand:
    """Email the owner after a single AOI analysis completes."""

    project_id: UUID
    aoi_id: UUID
    analysis_job_id: UUID
    owner_id: UUID


@dataclass(frozen=True)
class RankingLine:
    """One ranked neighborhood row for the comparison email."""

    rank: int
    name: str
    score: float
    priority_band: str


@dataclass(frozen=True)
class NotifyComparisonSummaryCommand:
    """Email a neighborhood comparison digest for a project."""

    project_id: UUID
    owner_id: UUID
    rankings: tuple[RankingLine, ...]
    notes: str = ""


class NotifyAnalysisCompleteUseCase:
    """Build and send a per-AOI analysis summary email."""

    def __init__(self, uow: UnitOfWork, notifier: EmailNotifier) -> None:
        self._uow = uow
        self._notifier = notifier

    def execute(self, command: NotifyAnalysisCompleteCommand) -> None:
        project = self._uow.projects.get_by_id(command.project_id)
        if project is None:
            raise NotFoundError(f"Project '{command.project_id}' was not found.")
        if project.owner_id != command.owner_id:
            raise ForbiddenError("You do not own this project.")

        owner = self._uow.users.get_by_id(project.owner_id)
        if owner is None:
            raise NotFoundError("Project owner was not found.")

        aoi = self._uow.areas_of_interest.get_by_id(command.aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{command.aoi_id}' was not found.")

        report = self._uow.analysis_reports.get_by_job_id(command.analysis_job_id)
        if report is None:
            raise NotFoundError("Analysis report was not found for this job.")

        subject, body = render_analysis_summary_email(
            recipient_name=owner.full_name or owner.email,
            project_name=project.name,
            aoi_name=aoi.name,
            aoi_kind=aoi.kind.value,
            executive_summary=report.executive_summary,
            priority_band=report.priority_band,
            score=report.score,
        )
        self._notifier.send(to_email=owner.email, subject=subject, body_text=body)


class NotifyComparisonSummaryUseCase:
    """Build and send a city vs neighborhoods comparison digest."""

    def __init__(self, uow: UnitOfWork, notifier: EmailNotifier) -> None:
        self._uow = uow
        self._notifier = notifier

    def execute(self, command: NotifyComparisonSummaryCommand) -> None:
        project = self._uow.projects.get_by_id(command.project_id)
        if project is None:
            raise NotFoundError(f"Project '{command.project_id}' was not found.")
        if project.owner_id != command.owner_id:
            raise ForbiddenError("You do not own this project.")

        owner = self._uow.users.get_by_id(project.owner_id)
        if owner is None:
            raise NotFoundError("Project owner was not found.")

        aois = self._uow.areas_of_interest.list_by_project(command.project_id, limit=100)
        city = next((a for a in aois if a.kind.value == "city"), None)

        if not command.rankings:
            raise ValidationError("At least one ranked neighborhood is required.")

        lines = [
            f"{row.rank}. {row.name} — score {row.score:.1f} ({row.priority_band})"
            for row in command.rankings
        ]
        subject, body = render_comparison_summary_email(
            recipient_name=owner.full_name or owner.email,
            project_name=project.name,
            city_name=city.name if city else None,
            ranking_lines=lines,
            notes=command.notes,
        )
        self._notifier.send(to_email=owner.email, subject=subject, body_text=body)
