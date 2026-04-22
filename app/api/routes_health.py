"""Health and status routes for the CoursePilot backend."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_HEALTH_PAYLOAD = {"status": "ok", "service": "coursepilot"}


@router.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight liveness check."""
    return _HEALTH_PAYLOAD


@router.get("/status")
def status() -> dict[str, str]:
    """Return a lightweight service status payload."""
    return _HEALTH_PAYLOAD
