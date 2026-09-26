"""Area of Interest aggregate – study boundary for a planning project."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from greencity.domain.entities.base import Entity
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry


class AoiKind(StrEnum):
    """Scale of an area of interest within a planning project."""

    CITY = "city"
    NEIGHBORHOOD = "neighborhood"


@dataclass(kw_only=True)
class AreaOfInterest(Entity):
    """Spatial study area belonging to a single project.

    Geometry is always WGS84 GeoJSON (Polygon or MultiPolygon). Analysis
    pipelines later clip imagery and indicators to this boundary.

    ``kind`` distinguishes the city-scale study area from neighborhood
    polygons used for comparison. Neighborhoods may optionally reference
    the city AOI via ``parent_aoi_id``.
    """

    project_id: UUID
    name: str
    description: str
    geometry: GeoJsonGeometry
    kind: AoiKind = AoiKind.NEIGHBORHOOD
    parent_aoi_id: UUID | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.description = self.description.strip()
        if not self.name:
            raise ValidationError("AOI name must not be empty.")
        if not isinstance(self.geometry, GeoJsonGeometry):
            raise ValidationError("AOI geometry must be a GeoJsonGeometry value object.")
        if not isinstance(self.kind, AoiKind):
            raise ValidationError("AOI kind must be a valid AoiKind.")
        if self.kind == AoiKind.CITY and self.parent_aoi_id is not None:
            raise ValidationError("City AOI cannot have a parent.")
        if self.kind == AoiKind.NEIGHBORHOOD and self.parent_aoi_id == self.id:
            raise ValidationError("AOI cannot be its own parent.")

    def rename(self, name: str) -> None:
        """Update the AOI display name."""

        cleaned = name.strip()
        if not cleaned:
            raise ValidationError("AOI name must not be empty.")
        self.name = cleaned
        self.touch()

    def update_description(self, description: str) -> None:
        """Replace the AOI description."""

        self.description = description.strip()
        self.touch()

    def replace_geometry(self, geometry: GeoJsonGeometry) -> None:
        """Replace the study boundary geometry."""

        if not isinstance(geometry, GeoJsonGeometry):
            raise ValidationError("AOI geometry must be a GeoJsonGeometry value object.")
        self.geometry = geometry
        self.touch()
