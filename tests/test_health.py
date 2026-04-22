"""Route-level tests for backend health endpoints."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_success() -> None:
    """Health endpoint should return a minimal success payload."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "coursepilot"}


def test_status_endpoint_returns_success() -> None:
    """Status endpoint should mirror the health payload."""
    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "coursepilot"}
