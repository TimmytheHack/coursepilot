"""FastAPI entrypoint for the CoursePilot backend."""

from fastapi import FastAPI

from app.api.routes_health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="CoursePilot API",
        version="0.1.0",
        description="Backend skeleton for CoursePilot.",
    )
    application.include_router(health_router)
    return application


app = create_app()
