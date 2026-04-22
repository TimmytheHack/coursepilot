"""Tests for the explicit planner graph execution flow."""

from app.agents.planner_graph import run_planner_graph
from app.models.schemas import PlanGenerateRequest
from app.services.memory_service import MemoryService


def test_run_planner_graph_executes_end_to_end(tmp_path) -> None:
    """The graph flow should produce the same validated plan variants as the service."""
    memory_service = MemoryService(db_path=tmp_path / "planner-graph.db")
    memory_service.save_user_profile(
        "u_graph",
        {"completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"]},
    )
    memory_service.upsert_memory(
        "u_graph",
        "preference",
        "preferred_directions",
        ["ai", "product"],
    )

    response = run_planner_graph(
        PlanGenerateRequest(
            user_id="u_graph",
            query="I want a balanced AI applications semester.",
            term="Fall 2026",
            max_courses=3,
            max_credits=12,
        ),
        memory_service=memory_service,
    )

    assert response.trace_id == "plan-u_graph-fall-2026"
    assert [plan.label for plan in response.plans] == ["balanced", "ambitious", "conservative"]
    assert all(plan.total_credits <= 12 for plan in response.plans)
    assert any("CS340" in plan.courses for plan in response.plans)
