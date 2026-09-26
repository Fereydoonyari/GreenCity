"""API contract tests for Green Deficiency Score / ranking."""

from fastapi.testclient import TestClient

from greencity.application.use_cases.aois import CreateAreaOfInterestUseCase
from greencity.application.use_cases.indicators import ComputeIndicatorsUseCase
from greencity.application.use_cases.projects import CreateProjectUseCase
from greencity.application.use_cases.scoring import RankNeighborhoodsUseCase, ScoreAoiUseCase
from greencity.application.use_cases.scoring_profiles import CreateScoringProfileUseCase
from greencity.domain.value_objects.geometry import GeoJsonGeometry
from greencity.domain.value_objects.urban_context import (
    BoundingBox,
    OsmContext,
)
from greencity.main import create_app
from greencity.presentation import dependencies as deps
from tests.auth_helpers import (
    configure_test_jwt,
    install_auth_overrides,
    register_and_auth_headers,
)
from tests.fakes import InMemoryUnitOfWork

SAMPLE_POLYGON = {
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
            total_road_length_m=4_000.0,
            total_park_area_m2=20_000.0,
            total_building_area_m2=40_000.0,
            aoi_area_m2=400_000.0,
            bounding_box=BoundingBox(2.35, 48.85, 2.36, 48.86),
        )



class _StubParkAccess:
    def compute(self, geometry, osm, *, walk_distance_m=300.0) -> float:
        return 0.5


def _build_client(monkeypatch) -> TestClient:
    configure_test_jwt(monkeypatch)
    uow = InMemoryUnitOfWork()
    app = create_app()
    compute = ComputeIndicatorsUseCase(uow, _StubOsm(), _StubParkAccess())

    app.dependency_overrides[deps.provide_unit_of_work] = lambda: uow
    install_auth_overrides(app, uow)
    app.dependency_overrides[deps.provide_create_project_use_case] = lambda: CreateProjectUseCase(
        uow
    )
    app.dependency_overrides[deps.provide_create_aoi_use_case] = (
        lambda: CreateAreaOfInterestUseCase(uow)
    )
    app.dependency_overrides[deps.provide_create_scoring_profile_use_case] = (
        lambda: CreateScoringProfileUseCase(uow)
    )
    app.dependency_overrides[deps.provide_score_aoi_use_case] = lambda: ScoreAoiUseCase(
        uow, compute
    )
    app.dependency_overrides[deps.provide_rank_neighborhoods_use_case] = (
        lambda: RankNeighborhoodsUseCase(uow)
    )
    return TestClient(app)


def test_score_and_rank_api(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    _user, headers = register_and_auth_headers(client, email="gds@city.gov")

    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"name": "GDS", "description": "", "status": "active"},
    ).json()
    aoi = client.post(
        "/api/v1/areas-of-interest",
        headers=headers,
        json={
            "project_id": project["id"],
            "name": "Zone",
            "geometry": SAMPLE_POLYGON,
            "kind": "city",
        },
    ).json()
    profile = client.post(
        "/api/v1/scoring-profiles",
        headers=headers,
        json={
            "name": "Default",
            "use_balanced_defaults": True,
            "is_default": True,
        },
    ).json()

    scored = client.post(
        f"/api/v1/scoring/aois/{aoi['id']}/score",
        headers=headers,
        json={
            "scoring_profile_id": profile["id"],
            "vegetation_coverage": 0.25,
            "green_area_m2": 5_000,
        },
    )
    assert scored.status_code == 200
    body = scored.json()
    assert 0 <= body["green_deficiency_score"]["score"] <= 100
    assert body["green_deficiency_score"]["priority_band"] in {"low", "medium", "high"}
    assert len(body["green_deficiency_score"]["contributions"]) == 4
    assert body["indicators"]["vegetation_coverage"] == 0.25

    ranked = client.post(
        "/api/v1/scoring/rank",
        headers=headers,
        json={
            "scoring_profile_id": profile["id"],
            "items": [
                {
                    "id": "north",
                    "label": "North",
                    "indicators": {
                        "vegetation_coverage": 0.9,
                        "green_area_per_m2": 0.4,
                        "road_density": 1000.0,
                        "built_up_ratio": 0.1,
                    },
                },
                {
                    "id": "south",
                    "label": "South",
                    "indicators": {
                        "vegetation_coverage": 0.05,
                        "green_area_per_m2": 0.02,
                        "road_density": 19000.0,
                        "built_up_ratio": 0.95,
                    },
                },
            ],
        },
    )
    assert ranked.status_code == 200
    rankings = ranked.json()["rankings"]
    assert rankings[0]["id"] == "south"
    assert rankings[0]["rank"] == 1
    assert rankings[1]["id"] == "north"
