"""Domain ports – abstract interfaces for persistence and external services."""

from greencity.domain.ports.health import HealthCheckPort
from greencity.domain.ports.imagery import ImageryAcquisitionPort
from greencity.domain.ports.indicators import ParkAccessibilityPort
from greencity.domain.ports.orchestration import AnalysisOrchestratorPort
from greencity.domain.ports.reporting import ReportExplainerPort
from greencity.domain.ports.repositories import (
    AnalysisJobRepository,
    AnalysisReportRepository,
    AreaOfInterestRepository,
    ProjectRepository,
    ScoringProfileRepository,
    UnitOfWork,
    UserRepository,
)
from greencity.domain.ports.security import PasswordHasher
from greencity.domain.ports.urban_context import OsmDataPort
from greencity.domain.ports.vegetation import VegetationPipelinePort

__all__ = [
    "AnalysisJobRepository",
    "AnalysisOrchestratorPort",
    "AnalysisReportRepository",
    "AreaOfInterestRepository",
    "HealthCheckPort",
    "ImageryAcquisitionPort",
    "OsmDataPort",
    "ParkAccessibilityPort",
    "PasswordHasher",
    "ProjectRepository",
    "ReportExplainerPort",
    "ScoringProfileRepository",
    "UnitOfWork",
    "UserRepository",
    "VegetationPipelinePort",
]
