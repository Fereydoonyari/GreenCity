"""Map between SQLAlchemy models and domain entities."""

from __future__ import annotations

from typing import Any

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.geometry.base import BaseGeometry

from greencity.domain.entities.analysis_job import AnalysisJob, AnalysisJobStatus
from greencity.domain.entities.analysis_report import AnalysisReport
from greencity.domain.entities.aoi import AoiKind, AreaOfInterest
from greencity.domain.entities.project import Project, ProjectStatus
from greencity.domain.entities.scoring_profile import ScoringProfile
from greencity.domain.entities.user import User
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.indicator_weights import IndicatorWeights
from greencity.infrastructure.persistence.models import (
    AnalysisJobModel,
    AnalysisReportModel,
    AreaOfInterestModel,
    ProjectModel,
    ScoringProfileModel,
    UserModel,
)


def user_to_domain(model: UserModel) -> User:
    """Convert a ``UserModel`` row into a domain ``User``."""

    return User(
        id=model.id,
        email=model.email,
        full_name=model.full_name,
        password_hash=model.password_hash,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_user_to_model(user: User, model: UserModel) -> None:
    """Copy domain user fields onto an ORM model instance."""

    model.id = user.id
    model.email = user.email
    model.full_name = user.full_name
    model.password_hash = user.password_hash
    model.is_active = user.is_active
    model.created_at = user.created_at
    model.updated_at = user.updated_at


def project_to_domain(model: ProjectModel) -> Project:
    """Convert a ``ProjectModel`` row into a domain ``Project``."""

    return Project(
        id=model.id,
        name=model.name,
        description=model.description,
        owner_id=model.owner_id,
        status=ProjectStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_project_to_model(project: Project, model: ProjectModel) -> None:
    """Copy domain project fields onto an ORM model instance."""

    model.id = project.id
    model.name = project.name
    model.description = project.description
    model.owner_id = project.owner_id
    model.status = project.status.value
    model.created_at = project.created_at
    model.updated_at = project.updated_at


def _as_multipolygon(geom: BaseGeometry) -> MultiPolygon:
    """Normalize Polygon / MultiPolygon into MultiPolygon for storage."""

    if isinstance(geom, MultiPolygon):
        return geom
    return MultiPolygon([geom])


def geojson_to_wkb_element(geometry: GeoJsonGeometry) -> Any:
    """Convert domain GeoJSON into a GeoAlchemy WKB element (EPSG:4326)."""

    shapely_geom = _as_multipolygon(shape(geometry.data))
    return from_shape(shapely_geom, srid=geometry.srid)


def wkb_element_to_geojson(geometry_column: Any) -> GeoJsonGeometry:
    """Convert a PostGIS geometry column value back to domain GeoJSON."""

    shapely_geom = to_shape(geometry_column)
    geojson: dict[str, Any] = mapping(shapely_geom)
    return GeoJsonGeometry(data=geojson)


def aoi_to_domain(model: AreaOfInterestModel) -> AreaOfInterest:
    """Convert an ``AreaOfInterestModel`` row into a domain entity."""

    return AreaOfInterest(
        id=model.id,
        project_id=model.project_id,
        name=model.name,
        description=model.description,
        geometry=wkb_element_to_geojson(model.geometry),
        kind=AoiKind(model.kind),
        parent_aoi_id=model.parent_aoi_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_aoi_to_model(aoi: AreaOfInterest, model: AreaOfInterestModel) -> None:
    """Copy domain AOI fields onto an ORM model instance."""

    model.id = aoi.id
    model.project_id = aoi.project_id
    model.name = aoi.name
    model.description = aoi.description
    model.kind = aoi.kind.value
    model.parent_aoi_id = aoi.parent_aoi_id
    model.geometry = geojson_to_wkb_element(aoi.geometry)
    model.created_at = aoi.created_at
    model.updated_at = aoi.updated_at


def scoring_profile_to_domain(model: ScoringProfileModel) -> ScoringProfile:
    """Convert a ``ScoringProfileModel`` row into a domain entity."""

    return ScoringProfile(
        id=model.id,
        owner_id=model.owner_id,
        name=model.name,
        description=model.description,
        weights=IndicatorWeights.from_mapping(model.weights),
        is_default=model.is_default,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_scoring_profile_to_model(profile: ScoringProfile, model: ScoringProfileModel) -> None:
    """Copy domain scoring profile fields onto an ORM model instance."""

    model.id = profile.id
    model.owner_id = profile.owner_id
    model.name = profile.name
    model.description = profile.description
    model.weights = profile.weights.as_dict()
    model.is_default = profile.is_default
    model.created_at = profile.created_at
    model.updated_at = profile.updated_at


def analysis_job_to_domain(model: AnalysisJobModel) -> AnalysisJob:
    """Convert an ``AnalysisJobModel`` row into a domain entity."""

    return AnalysisJob(
        id=model.id,
        project_id=model.project_id,
        aoi_id=model.aoi_id,
        scoring_profile_id=model.scoring_profile_id,
        status=AnalysisJobStatus(model.status),
        current_step=model.current_step,
        progress_pct=model.progress_pct,
        error_message=model.error_message,
        started_at=model.started_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_analysis_job_to_model(job: AnalysisJob, model: AnalysisJobModel) -> None:
    """Copy domain analysis job fields onto an ORM model instance."""

    model.id = job.id
    model.project_id = job.project_id
    model.aoi_id = job.aoi_id
    model.scoring_profile_id = job.scoring_profile_id
    model.status = job.status.value
    model.current_step = job.current_step
    model.progress_pct = job.progress_pct
    model.error_message = job.error_message
    model.started_at = job.started_at
    model.completed_at = job.completed_at
    model.created_at = job.created_at
    model.updated_at = job.updated_at


def analysis_report_to_domain(model: AnalysisReportModel) -> AnalysisReport:
    """Convert an ``AnalysisReportModel`` row into a domain entity."""

    return AnalysisReport(
        id=model.id,
        analysis_job_id=model.analysis_job_id,
        aoi_id=model.aoi_id,
        scoring_profile_id=model.scoring_profile_id,
        headline=model.headline,
        executive_summary=model.executive_summary,
        priority_band=model.priority_band,
        score=float(model.score),
        drivers=list(model.drivers or []),
        recommendations=list(model.recommendations or []),
        methodology_notes=model.methodology_notes,
        source=model.source,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_analysis_report_to_model(report: AnalysisReport, model: AnalysisReportModel) -> None:
    """Copy domain analysis report fields onto an ORM model instance."""

    model.id = report.id
    model.analysis_job_id = report.analysis_job_id
    model.aoi_id = report.aoi_id
    model.scoring_profile_id = report.scoring_profile_id
    model.headline = report.headline
    model.executive_summary = report.executive_summary
    model.priority_band = report.priority_band
    model.score = report.score
    model.drivers = list(report.drivers)
    model.recommendations = list(report.recommendations)
    model.methodology_notes = report.methodology_notes
    model.source = report.source
    model.created_at = report.created_at
    model.updated_at = report.updated_at
