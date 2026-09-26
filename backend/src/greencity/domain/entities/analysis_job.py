"""Analysis job aggregate – lifecycle for a green-deficiency analysis run."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from greencity.domain.entities.base import Entity
from greencity.domain.exceptions import ConflictError, ValidationError


class AnalysisJobStatus(StrEnum):
    """Lifecycle states for an analysis job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL = frozenset(
    {
        AnalysisJobStatus.COMPLETED,
        AnalysisJobStatus.FAILED,
        AnalysisJobStatus.CANCELLED,
    }
)


@dataclass(kw_only=True)
class AnalysisJob(Entity):
    """A single analysis run scoped to a project AOI and scoring profile.

    Lifecycle transitions live on this aggregate. The analysis pipeline
    advances ``current_step`` / ``progress_pct`` while the job is
    ``running``.
    """

    project_id: UUID
    aoi_id: UUID
    scoring_profile_id: UUID
    status: AnalysisJobStatus = AnalysisJobStatus.QUEUED
    current_step: str = "queued"
    progress_pct: int = 0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, AnalysisJobStatus):
            self.status = AnalysisJobStatus(self.status)
        self.current_step = self.current_step.strip() or self.status.value
        self._validate_progress(self.progress_pct)

    @staticmethod
    def _validate_progress(progress_pct: int) -> None:
        if progress_pct < 0 or progress_pct > 100:
            raise ValidationError("progress_pct must be between 0 and 100.")

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` when the job can no longer change status."""

        return self.status in _TERMINAL

    def start(self) -> None:
        """Transition ``queued`` → ``running``."""

        if self.status != AnalysisJobStatus.QUEUED:
            raise ConflictError(
                f"Cannot start job in status '{self.status.value}' (expected queued)."
            )
        self.status = AnalysisJobStatus.RUNNING
        self.current_step = "running"
        self.progress_pct = max(self.progress_pct, 1)
        self.started_at = datetime.now(UTC)
        self.error_message = None
        self.touch()

    def update_progress(self, *, current_step: str, progress_pct: int) -> None:
        """Update progress while the job is running."""

        if self.status != AnalysisJobStatus.RUNNING:
            raise ConflictError("Progress can only be updated while the job is running.")
        cleaned = current_step.strip()
        if not cleaned:
            raise ValidationError("current_step must not be empty.")
        self._validate_progress(progress_pct)
        self.current_step = cleaned
        self.progress_pct = progress_pct
        self.touch()

    def complete(self) -> None:
        """Transition ``running`` → ``completed``."""

        if self.status != AnalysisJobStatus.RUNNING:
            raise ConflictError(
                f"Cannot complete job in status '{self.status.value}' (expected running)."
            )
        self.status = AnalysisJobStatus.COMPLETED
        self.current_step = "completed"
        self.progress_pct = 100
        self.completed_at = datetime.now(UTC)
        self.error_message = None
        self.touch()

    def fail(self, message: str) -> None:
        """Transition ``running`` (or ``queued``) → ``failed``."""

        if self.status not in {AnalysisJobStatus.QUEUED, AnalysisJobStatus.RUNNING}:
            raise ConflictError(
                f"Cannot fail job in status '{self.status.value}'."
            )
        cleaned = message.strip()
        if not cleaned:
            raise ValidationError("Failure message must not be empty.")
        self.status = AnalysisJobStatus.FAILED
        self.current_step = "failed"
        self.error_message = cleaned
        self.completed_at = datetime.now(UTC)
        self.touch()

    def cancel(self) -> None:
        """Transition ``queued`` / ``running`` → ``cancelled``."""

        if self.status not in {AnalysisJobStatus.QUEUED, AnalysisJobStatus.RUNNING}:
            raise ConflictError(
                f"Cannot cancel job in status '{self.status.value}'."
            )
        self.status = AnalysisJobStatus.CANCELLED
        self.current_step = "cancelled"
        self.completed_at = datetime.now(UTC)
        self.touch()
