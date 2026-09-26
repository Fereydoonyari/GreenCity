"""Area of Interest CRUD use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from greencity.domain.entities.aoi import AoiKind, AreaOfInterest
from greencity.domain.exceptions import ConflictError, NotFoundError, ValidationError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.value_objects.geometry import GeoJsonGeometry


def _geometry_from_payload(geometry: dict[str, Any] | GeoJsonGeometry) -> GeoJsonGeometry:
    """Normalize API/use-case geometry input into a value object."""

    if isinstance(geometry, GeoJsonGeometry):
        return geometry
    if not isinstance(geometry, dict):
        raise ValidationError("Geometry must be a GeoJSON object.")
    # Accept a Feature by unwrapping its geometry.
    if geometry.get("type") == "Feature":
        inner = geometry.get("geometry")
        if not isinstance(inner, dict):
            raise ValidationError("GeoJSON Feature must contain a geometry object.")
        return GeoJsonGeometry(data=inner)
    if geometry.get("type") == "FeatureCollection":
        features = geometry.get("features")
        if not isinstance(features, list) or len(features) != 1:
            raise ValidationError(
                "FeatureCollection must contain exactly one Feature for AOI create/update."
            )
        return _geometry_from_payload(features[0])
    return GeoJsonGeometry(data=geometry)


@dataclass(frozen=True)
class CreateAreaOfInterestCommand:
    """Input for creating an AOI."""

    project_id: UUID
    name: str
    description: str
    geometry: dict[str, Any]
    kind: AoiKind = AoiKind.NEIGHBORHOOD
    parent_aoi_id: UUID | None = None


@dataclass(frozen=True)
class UpdateAreaOfInterestCommand:
    """Input for updating mutable AOI fields."""

    name: str | None = None
    description: str | None = None
    geometry: dict[str, Any] | None = None


class CreateAreaOfInterestUseCase:
    """Create an AOI for an existing project."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, command: CreateAreaOfInterestCommand) -> AreaOfInterest:
        """Persist a new AOI or raise if the project is missing."""

        project = self._uow.projects.get_by_id(command.project_id)
        if project is None:
            raise NotFoundError(f"Project '{command.project_id}' was not found.")

        parent_id = command.parent_aoi_id
        if command.kind == AoiKind.CITY:
            if parent_id is not None:
                raise ValidationError("City AOI cannot have a parent.")
            existing = self._uow.areas_of_interest.list_by_project(
                command.project_id, limit=100
            )
            if any(a.kind == AoiKind.CITY for a in existing):
                raise ConflictError("This project already has a city-scale AOI.")
        elif parent_id is not None:
            parent = self._uow.areas_of_interest.get_by_id(parent_id)
            if parent is None:
                raise NotFoundError(f"Parent AOI '{parent_id}' was not found.")
            if parent.project_id != command.project_id:
                raise ValidationError("Parent AOI must belong to the same project.")
            if parent.kind != AoiKind.CITY:
                raise ValidationError("Neighborhood parent must be a city-scale AOI.")

        aoi = AreaOfInterest(
            project_id=command.project_id,
            name=command.name,
            description=command.description,
            geometry=_geometry_from_payload(command.geometry),
            kind=command.kind,
            parent_aoi_id=parent_id,
        )
        created = self._uow.areas_of_interest.add(aoi)
        self._uow.commit()
        return created


class GetAreaOfInterestUseCase:
    """Fetch a single AOI by id."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, aoi_id: UUID) -> AreaOfInterest:
        """Return the AOI or raise ``NotFoundError``."""

        aoi = self._uow.areas_of_interest.get_by_id(aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{aoi_id}' was not found.")
        return aoi


class ListAreasOfInterestUseCase:
    """List AOIs for a project."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        project_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AreaOfInterest]:
        """Return a page of AOIs for ``project_id``."""

        project = self._uow.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project '{project_id}' was not found.")

        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        return self._uow.areas_of_interest.list_by_project(
            project_id, limit=limit, offset=offset
        )


class UpdateAreaOfInterestUseCase:
    """Update mutable AOI fields."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, aoi_id: UUID, command: UpdateAreaOfInterestCommand) -> AreaOfInterest:
        """Apply updates or raise ``NotFoundError``."""

        aoi = self._uow.areas_of_interest.get_by_id(aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{aoi_id}' was not found.")

        if command.name is not None:
            aoi.rename(command.name)
        if command.description is not None:
            aoi.update_description(command.description)
        if command.geometry is not None:
            aoi.replace_geometry(_geometry_from_payload(command.geometry))

        saved = self._uow.areas_of_interest.save(aoi)
        self._uow.commit()
        return saved


class DeleteAreaOfInterestUseCase:
    """Permanently delete an AOI.

    Also removes dependent analysis jobs (and cascaded reports) so the
    foreign-key constraint on ``analysis_jobs.aoi_id`` does not block delete.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, aoi_id: UUID) -> None:
        """Delete the AOI or raise ``NotFoundError``."""

        if self._uow.areas_of_interest.get_by_id(aoi_id) is None:
            raise NotFoundError(f"Area of interest '{aoi_id}' was not found.")

        # Reports reference AOIs with RESTRICT; delete jobs first so DB
        # ON DELETE CASCADE clears reports, then remove any leftover reports.
        for job in self._uow.analysis_jobs.list_by_aoi(aoi_id, limit=1000):
            self._uow.analysis_jobs.delete(job.id)
        for report in self._uow.analysis_reports.list_by_aoi(aoi_id, limit=1000):
            self._uow.analysis_reports.delete(report.id)

        deleted = self._uow.areas_of_interest.delete(aoi_id)
        if not deleted:
            raise NotFoundError(f"Area of interest '{aoi_id}' was not found.")
        self._uow.commit()
