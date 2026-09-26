"""FastAPI application factory and ASGI entrypoint.

Creates the app, configures middleware, and mounts versioned routers.
Composition of use cases happens via presentation dependencies / DI module.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from greencity import __version__
from greencity.config import Settings, get_settings
from greencity.presentation.api.v1 import api_v1_router
from greencity.presentation.exception_handlers import register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        settings: Optional settings override (tests may inject custom values).

    Returns:
        Configured ``FastAPI`` instance.
    """

    resolved = settings or get_settings()
    app = FastAPI(
        title=resolved.app_name,
        version=__version__,
        debug=resolved.app_debug,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=resolved.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        """Simple root redirect hint for humans hitting the base URL."""

        return {
            "name": resolved.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": f"{resolved.api_v1_prefix}/health",
        }

    return app


app = create_app()
