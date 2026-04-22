"""Service-level tests for deterministic semester planning."""

from app.models.schemas import PlanGenerateRequest
from app.services.planning_service import generate_semester_plan


def test_generate_semester_plan_builds_distinct_validated_variants() -> None:
    """The planning service should assemble multiple validated plan variants."""
    completed_courses = ["CS101", "CS120", "CS201", "CS240", "CS330"]
    response = generate_semester_plan(
        PlanGenerateRequest(
            user_id="u_service",
            query="I want a balanced AI applications semester.",
            term="Fall 2026",
            completed_courses=completed_courses,
            preferred_directions=["ai", "product"],
            max_courses=3,
            max_credits=12,
        )
    )

    plan_labels = [plan.label for plan in response.plans]
    plan_courses = [tuple(plan.courses) for plan in response.plans]

    assert response.trace_id == "plan-u_service-fall-2026"
    assert plan_labels == ["balanced", "ambitious", "conservative"]
    assert len(plan_courses) == len(set(plan_courses))
    assert all(not set(plan.courses).intersection(completed_courses) for plan in response.plans)
    assert all(plan.total_credits <= 12 for plan in response.plans)
    assert any("CS340" in plan.courses or "CS360" in plan.courses for plan in response.plans)
