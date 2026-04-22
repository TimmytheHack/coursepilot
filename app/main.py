"""FastAPI entrypoint for the CoursePilot backend."""

from fastapi import FastAPI

from app.api import courses_router, debug_router, eval_router, health_router, plan_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="CoursePilot API",
        version="0.1.0",
        description="Backend skeleton for CoursePilot.",
    )
    application.include_router(health_router)
    application.include_router(plan_router)
    application.include_router(courses_router)
    application.include_router(debug_router)
    application.include_router(eval_router)
    return application


app = create_app()
