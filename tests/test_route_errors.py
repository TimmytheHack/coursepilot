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


def test_course_search_allows_empty_query_with_stable_empty_results() -> None:
    """Course search should handle empty query strings safely."""
    response = client.get("/courses/search", params={"q": ""})

    assert response.status_code == 200
    assert response.json() == {"query": "", "results": []}


def test_refine_plan_rejects_underspecified_request() -> None:
    """Refinement should return a clear 400 when the request is too vague."""
    response = client.post(
        "/plan/refine",
        json={
            "user_id": "u_refine_bad",
            "prior_plan": {
                "plan_id": "plan_ambitious",
                "query": "I want an AI applications semester.",
                "term": "Fall 2026",
                "courses": ["CS210", "CS310", "CS340"],
                "completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"],
                "preferred_directions": ["ai", "product"],
                "max_courses": 3,
                "max_credits": 12,
            },
            "query": "Change it.",
        },
    )

    assert response.status_code == 400
    assert "too vague" in response.json()["detail"]


def test_refine_plan_rejects_impossible_constraints() -> None:
    """Refinement should return a clear 400 when requested constraints cannot be met."""
    response = client.post(
        "/plan/refine",
        json={
            "user_id": "u_refine_impossible",
            "prior_plan": {
                "plan_id": "plan_ambitious",
                "query": "I want an AI applications semester.",
                "term": "Fall 2026",
                "courses": ["CS210", "CS310", "CS340"],
                "completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"],
                "preferred_directions": ["ai", "product"],
                "max_courses": 3,
                "max_credits": 12,
            },
            "query": "Keep CS340 and avoid morning classes.",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "No validated refinement could be generated for the requested changes."}
