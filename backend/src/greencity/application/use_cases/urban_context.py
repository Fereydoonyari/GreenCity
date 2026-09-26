"""Use cases for OSM urban context."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from greencity.domain.exceptions import NotFoundError
from greencity.domain.ports.repositories import UnitOfWork
from greencity.domain.ports.urban_context import OsmDataPort
from greencity.domain.value_objects.urban_context import OsmContext


@dataclass(frozen=True)
class FetchOsmContextCommand:
    """Input for fetching OSM features for an AOI."""

    aoi_id: UUID


class FetchOsmContextUseCase:
    """Load an AOI and fetch OSM roads / parks / buildings for its geometry."""

    def __init__(self, uow: UnitOfWork, osm: OsmDataPort) -> None:
        self._uow = uow
        self._osm = osm

    def execute(self, command: FetchOsmContextCommand) -> OsmContext:
        """Return OSM urban context for the AOI, or raise if missing."""

        aoi = self._uow.areas_of_interest.get_by_id(command.aoi_id)
        if aoi is None:
            raise NotFoundError(f"Area of interest '{command.aoi_id}' was not found.")
        return self._osm.fetch(aoi.geometry)
