"""Route-level error handling tests for reliability hardening."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_generate_plan_rejects_unknown_completed_course_ids() -> None:
    """Planning should fail loudly when completed courses are not in the catalog."""
    response = client.post(
        "/plan/generate",
        json={
            "user_id": "u_bad_completed",
            "query": "Build me a balanced semester.",
            "term": "Fall 2026",
            "completed_courses": ["CS999"],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unknown completed course IDs: CS999"}


def test_generate_plan_rejects_impossible_constraints() -> None:
    """Planning should return a clear 400 when constraints leave no valid plan."""
    response = client.post(
        "/plan/generate",
        json={
            "user_id": "u_tight_constraints",
            "query": "Build me a systems semester.",
            "term": "Spring 2026",
            "completed_courses": ["CS101", "CS120", "CS201", "CS210"],
            "preferred_directions": ["systems"],
            "max_courses": 3,
            "max_credits": 3,
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "No valid plans could be generated from the current request constraints."}


def test_generate_plan_rejects_malformed_request_body() -> None:
    """Missing required request fields should surface as validation errors."""
    response = client.post(
        "/plan/generate",
        json={
            "user_id": "u_missing_query",
            "term": "Fall 2026",
        },
    )

    assert response.status_code == 422


def test_course_search_rejects_empty_query() -> None:
    """Course search should reject empty query strings."""
    response = client.get("/courses/search", params={"q": ""})

    assert response.status_code == 422
