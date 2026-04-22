"""Route-level tests for typed placeholder API contracts."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_includes_day_two_routes() -> None:
    """OpenAPI should expose the main placeholder endpoints."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/plan/generate" in paths
    assert "/plan/refine" in paths
    assert "/courses/search" in paths
    assert "/eval/run" in paths


def test_generate_plan_returns_typed_placeholder_response() -> None:
    """Plan generation route should return validated deterministic plans."""
    completed_courses = ["CS101", "CS120", "CS201", "CS240", "CS330"]
    response = client.post(
        "/plan/generate",
        json={
            "user_id": "u_001",
            "query": "Build me a balanced semester focused on AI applications.",
            "term": "Fall 2026",
            "completed_courses": completed_courses,
            "preferred_directions": ["ai", "product"],
            "max_courses": 3,
            "max_credits": 12,
        },
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["trace_id"] == "plan-u_001-fall-2026"
    assert [plan["label"] for plan in payload["plans"]] == ["balanced", "ambitious", "conservative"]
    plan_course_sets = [tuple(plan["courses"]) for plan in payload["plans"]]
    assert len(plan_course_sets) == len(set(plan_course_sets))
    assert all(not set(plan["courses"]).intersection(completed_courses) for plan in payload["plans"])
    assert all(plan["validation_facts"] for plan in payload["plans"])
    assert all(plan["total_credits"] <= 12 for plan in payload["plans"])
    assert payload["summary"].startswith("Generated 3 validated plan option")


def test_refine_plan_returns_typed_placeholder_response() -> None:
    """Plan refinement route should return the expected placeholder schema."""
    response = client.post(
        "/plan/refine",
        json={
            "user_id": "u_001",
            "previous_plan_id": "plan_a",
            "query": "Make this lighter.",
        },
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["trace_id"] == "placeholder-refine-u_001"
    assert payload["plans"][0]["label"] == "refined-placeholder"


def test_course_search_returns_typed_placeholder_response() -> None:
    """Course search route should return the expected placeholder schema."""
    response = client.get("/courses/search", params={"q": "ai"})

    payload = response.json()

    assert response.status_code == 200
    assert payload["query"] == "ai"
    assert payload["results"][0]["course_id"] == "CS000"


def test_eval_run_returns_typed_placeholder_response() -> None:
    """Eval run route should return the expected placeholder schema."""
    response = client.post("/eval/run")

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "placeholder-eval-run",
        "status": "not_started",
        "summary": "Evaluation pipeline has not been implemented yet.",
    }
