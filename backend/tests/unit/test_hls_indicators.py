"""Unit tests for HLS-backed vegetation path in ComputeIndicatorsUseCase."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from greencity.application.use_cases.aois import CreateAreaOfInterestCommand, CreateAreaOfInterestUseCase
from greencity.application.use_cases.indicators import (
    ComputeIndicatorsCommand,
    ComputeIndicatorsUseCase,
)
from greencity.application.use_cases.projects import CreateProjectCommand, CreateProjectUseCase
from greencity.application.use_cases.users import CreateUserCommand, CreateUserUseCase
from greencity.domain.exceptions import ValidationError
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.imagery import RedNirScene
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
)
from greencity.infrastructure.imagery import NumpyVegetationPipeline
from tests.fakes import FakePasswordHasher, InMemoryUnitOfWork

SAMPLE = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.35, 48.85],
            [2.36, 48.85],
            [2.36, 48.86],
            [2.35, 48.86],
            [2.35, 48.85],
        ]
    ],
}


class _StubOsm:
    def fetch(self, geometry: GeoJsonGeometry) -> OsmContext:
        return OsmContext(
            roads=(),
            parks=(),
            buildings=(),
            total_road_length_m=500.0,
            total_park_area_m2=10_000.0,
            total_building_area_m2=20_000.0,
            aoi_area_m2=400_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )



class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.5


class _FakeHls:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def acquire_red_nir(self, geometry: GeoJsonGeometry) -> RedNirScene:
        self.calls += 1
        if self.fail:
            raise ValidationError("no HLS scene")
        # Synthetic vegetated patch: high NIR, low Red → high NDVI
        red = np.full((20, 20), 0.1, dtype=np.float64)
        nir = np.full((20, 20), 0.6, dtype=np.float64)
        return RedNirScene(
            red_band=red,
            nir_band=nir,
            nodata_mask=np.zeros((20, 20), dtype=bool),
            pixel_size_m=30.0,
            source="hls_ndvi",
            granule_id="HLS.S30.T31UDQ.test",
            acquired_at=datetime.now(UTC),
            product="HLSS30",
            transform=(0.001, 0.0, 2.35, 0.0, -0.001, 48.86),
            crs="EPSG:4326",
        )


def _seed_aoi(uow: InMemoryUnitOfWork):
    user = CreateUserUseCase(uow, FakePasswordHasher()).execute(
        CreateUserCommand(email="hls@example.com", full_name="H", password="secret123")
    )
    project = CreateProjectUseCase(uow).execute(
        CreateProjectCommand(name="P", description="", owner_id=user.id)
    )
    return CreateAreaOfInterestUseCase(uow).execute(
        CreateAreaOfInterestCommand(
            project_id=project.id, name="A", description="", geometry=SAMPLE
        )
    )


def test_hls_path_sets_vegetation_source() -> None:
    uow = InMemoryUnitOfWork()
    aoi = _seed_aoi(uow)
    hls = _FakeHls()
    uc = ComputeIndicatorsUseCase(
        uow,
        _StubOsm(),
        _StubParkAccess(),
        imagery=hls,
        vegetation_pipeline=NumpyVegetationPipeline(),
    )
    result = uc.execute(ComputeIndicatorsCommand(aoi_id=aoi.id))

    assert hls.calls == 1
    assert result.vegetation_source.startswith("hls_ndvi:")
    assert "HLS.S30" in result.vegetation_source
    assert result.indicators.vegetation_coverage > 0.5
    assert result.green_area_source == "hls_ndvi"
    assert result.vegetation_mask is not None
    assert result.vegetation_mask["type"] == "FeatureCollection"
    assert len(result.vegetation_mask["features"]) >= 1


def test_hls_failure_falls_back_to_osm() -> None:
    uow = InMemoryUnitOfWork()
    aoi = _seed_aoi(uow)
    hls = _FakeHls(fail=True)
    uc = ComputeIndicatorsUseCase(
        uow,
        _StubOsm(),
        _StubParkAccess(),
        imagery=hls,
        vegetation_pipeline=NumpyVegetationPipeline(),
    )
    result = uc.execute(ComputeIndicatorsCommand(aoi_id=aoi.id))

    assert hls.calls == 1
    assert result.vegetation_source == "osm_park_coverage_proxy"
    assert result.green_area_source == "osm_park_area"


def test_explicit_override_skips_hls() -> None:
    uow = InMemoryUnitOfWork()
    aoi = _seed_aoi(uow)
    hls = _FakeHls()
    uc = ComputeIndicatorsUseCase(
        uow,
        _StubOsm(),
        _StubParkAccess(),
        imagery=hls,
        vegetation_pipeline=NumpyVegetationPipeline(),
    )
    result = uc.execute(
        ComputeIndicatorsCommand(
            aoi_id=aoi.id,
            vegetation_coverage=0.42,
            green_area_m2=8_000,
        )
    )

    assert hls.calls == 0
    assert result.vegetation_source == "provided"
    assert result.indicators.vegetation_coverage == pytest.approx(0.42)
