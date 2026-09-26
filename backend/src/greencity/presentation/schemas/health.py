"""Health-related API schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """HTTP representation of application health status."""

    status: str = Field(description="Overall status: healthy or degraded.")
    database: str = Field(description="Database readiness: up or down.")
    version: str = Field(description="Application version.")
