"""Application configuration loaded from environment variables.

Configuration lives outside domain logic so secrets and deployment
settings never leak into business rules.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for GreenCity AI.

    Values are read from environment variables and optional ``.env`` files.
    Nested list settings such as ``CORS_ORIGINS`` accept JSON arrays.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="GreenCity AI", description="Human-readable application name.")
    app_env: str = Field(default="development", description="Environment name.")
    app_debug: bool = Field(default=True, description="Enable debug behaviours.")
    api_v1_prefix: str = Field(default="/api/v1", description="REST API version prefix.")

    database_url: str = Field(
        default="postgresql+psycopg://greencity:greencity@localhost:5432/greencity",
        description="SQLAlchemy database URL (PostgreSQL + PostGIS).",
    )

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        description="Allowed CORS origins for the SPA.",
    )

    nasa_earthaccess_username: str = Field(default="", description="NASA EarthAccess username.")
    nasa_earthaccess_password: str = Field(default="", description="NASA EarthAccess password.")
    openai_api_key: str = Field(default="", description="LLM API key for the planning agent.")
    llm_model: str = Field(default="gpt-4o-mini", description="Default LLM model identifier.")
    overpass_url: str = Field(
        default="https://overpass-api.de/api/interpreter",
        description="Overpass API interpreter URL (mirrors used automatically on failure).",
    )
    hls_enabled: bool = Field(
        default=True,
        description="Prefer HLS NDVI when EarthAccess credentials are configured.",
    )
    hls_lookback_days: int = Field(
        default=180,
        ge=1,
        le=730,
        description="How far back to search for HLS granules.",
    )
    hls_max_cloud_cover: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Maximum cloud cover (%) accepted for HLS granules.",
    )
    landsat_enabled: bool = Field(
        default=True,
        description="Prefer Landsat C2 L2 surface temperature when EarthAccess is configured.",
    )
    landsat_lookback_days: int = Field(
        default=180,
        ge=1,
        le=730,
        description="How far back to search for Landsat ST granules.",
    )
    landsat_max_cloud_cover: float = Field(
        default=60.0,
        ge=0.0,
        le=100.0,
        description="Maximum cloud cover (%) accepted for Landsat ST granules.",
    )

    # Auth
    jwt_secret: str = Field(
        default="dev-only-change-me-greencity-jwt-secret",
        description="HS256 secret for access tokens (set a strong value in production).",
    )
    jwt_expire_minutes: int = Field(
        default=10_080,
        ge=5,
        description="Access token lifetime in minutes (default 7 days).",
    )

    # Email notifications (analysis summary)
    email_enabled: bool = Field(
        default=False,
        description="When true and SMTP_HOST is set, send real email; otherwise log stub.",
    )
    smtp_host: str = Field(default="", description="SMTP server hostname.")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP port.")
    smtp_username: str = Field(default="", description="SMTP auth username.")
    smtp_password: str = Field(default="", description="SMTP auth password.")
    smtp_from: str = Field(
        default="noreply@greencity.local",
        description="From address for transactional email.",
    )
    smtp_use_tls: bool = Field(default=True, description="Use STARTTLS for SMTP.")
    email_on_analysis_complete: bool = Field(
        default=True,
        description="Send a summary email to the project owner after each successful analysis run.",
    )

    # Overpass resilience
    overpass_mirror_urls: list[str] = Field(
        default_factory=lambda: [
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
        ],
        description="Overpass mirrors raced in parallel with OVERPASS_URL.",
    )
    overpass_timeout_s: float = Field(
        default=40.0,
        gt=0.0,
        description="Per-endpoint HTTP timeout in seconds.",
    )
    overpass_retries_per_mirror: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Attempts per endpoint before giving up on that endpoint.",
    )
    overpass_cache_ttl_s: int = Field(
        default=86_400,
        ge=0,
        description="Disk cache TTL for Overpass JSON (0 disables cache).",
    )
    overpass_cache_dir: str = Field(
        default=".cache/overpass",
        description="Directory for Overpass response cache files.",
    )

    @property
    def earthaccess_configured(self) -> bool:
        """True when NASA Earthdata login credentials are present."""

        return bool(
            self.nasa_earthaccess_username.strip() and self.nasa_earthaccess_password.strip()
        )

    @property
    def hls_acquisition_enabled(self) -> bool:
        """True when HLS should be attempted for vegetation analysis."""

        return self.hls_enabled and self.earthaccess_configured

    @property
    def landsat_acquisition_enabled(self) -> bool:
        """True when Landsat ST heat overlay should be attempted.

        Planetary Computer hosts SAS-signed COGs; Earthdata login is not required.
        """

        return self.landsat_enabled


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Caching avoids re-parsing environment variables on every request while
    still allowing tests to clear the cache via ``get_settings.cache_clear()``.
    """

    return Settings()
