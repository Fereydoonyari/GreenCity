"""API v1 router aggregation."""

from fastapi import APIRouter

from greencity.presentation.api.v1 import (
    agent,
    analysis_jobs,
    aois,
    auth,
    health,
    indicators,
    notifications,
    projects,
    reports,
    scoring,
    scoring_profiles,
    urban_context,
    users,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(auth.router, tags=["auth"])
api_v1_router.include_router(users.router, tags=["users"])
api_v1_router.include_router(projects.router, tags=["projects"])
api_v1_router.include_router(aois.router, tags=["areas-of-interest"])
api_v1_router.include_router(scoring_profiles.router, tags=["scoring-profiles"])
api_v1_router.include_router(analysis_jobs.router, tags=["analysis-jobs"])
api_v1_router.include_router(reports.router, tags=["reports"])
api_v1_router.include_router(notifications.router, tags=["notifications"])
api_v1_router.include_router(agent.router)
api_v1_router.include_router(urban_context.router)
api_v1_router.include_router(indicators.router)
api_v1_router.include_router(scoring.router)
