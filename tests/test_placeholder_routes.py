"""Route-level tests for the current API contracts."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_includes_day_two_routes() -> None:
    """OpenAPI should expose the main placeholder endpoints."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/debug/traces" in paths
    assert "/debug/memory" in paths
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


def test_refine_plan_returns_validated_refined_response() -> None:
    """Plan refinement route should return one validated deterministic revision."""
    response = client.post(
        "/plan/refine",
        json={
            "user_id": "u_001",
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
            "query": "Keep CS340 but replace CS310 with something lighter.",
        },
    )

    payload = response.json()

    assert response.status_code == 200
    assert payload["trace_id"] == "refine-u_001-fall-2026"
    assert len(payload["plans"]) == 1
    assert payload["plans"][0]["label"] == "refined"
    assert "CS340" in payload["plans"][0]["courses"]
    assert "CS310" not in payload["plans"][0]["courses"]


def test_course_search_returns_ranked_results() -> None:
    """Course search route should return deterministic ranked results."""
    response = client.get("/courses/search", params={"q": "operating systems"})

    payload = response.json()

    assert response.status_code == 200
    assert payload["query"] == "operating systems"
    assert payload["results"][0]["course_id"] == "CS320"
    assert payload["results"][0]["department"] == "CS"
    assert payload["results"][0]["credits"] == 4


def test_course_search_returns_empty_results_for_empty_query() -> None:
    """Course search should handle empty queries safely and deterministically."""
    response = client.get("/courses/search", params={"q": ""})

    assert response.status_code == 200
    assert response.json() == {"query": "", "results": []}


def test_course_search_returns_empty_results_for_no_match_query() -> None:
    """Course search should return an empty list when nothing matches."""
    response = client.get("/courses/search", params={"q": "ancient pottery"})

    assert response.status_code == 200
    assert response.json() == {"query": "ancient pottery", "results": []}


def test_course_search_returns_fixture_catalog_match() -> None:
    """Course search should search over the current catalog fixture data."""
    response = client.get("/courses/search", params={"q": "visualization"})

    payload = response.json()

    assert response.status_code == 200
    assert [result["course_id"] for result in payload["results"]] == ["CS380"]


def test_eval_run_returns_eval_summary_response() -> None:
    """Eval run route should return the expected evaluation summary schema."""
    response = client.post("/eval/run")

    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "completed"
    assert payload["run_id"].startswith("eval-")
    assert payload["metrics"]["schema_success_rate"] >= 0.0
    assert payload["report_path"].endswith(".json")
