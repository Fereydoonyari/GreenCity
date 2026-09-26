"""Shared domain entities and base types."""

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.entities.aoi import AreaOfInterest
from greencity.domain.entities.base import Entity
from greencity.domain.entities.project import Project, ProjectStatus
from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.domain.entities.user import User

__all__ = [
    "AnalysisJob",
    "AnalysisJobStatus",
    "AnalysisReport",
    "AreaOfInterest",
    "Entity",
    "Project",
    "ProjectStatus",
    "ScoringProfile",
    "User",
]
