"""Integration tests for planning with persisted user memory."""

from app.models.schemas import PlanGenerateRequest
from app.services.memory_service import MemoryService
from app.services.planning_service import generate_semester_plan


def test_generate_semester_plan_uses_saved_memory_when_request_omits_context(tmp_path) -> None:
    """Planning should load completed courses and preferences from SQLite memory."""
    memory_service = MemoryService(db_path=tmp_path / "memory.db")
    memory_service.save_user_profile(
        "u_memory_plan",
        {"completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"]},
    )
    memory_service.upsert_memory(
        "u_memory_plan",
        "preference",
        "preferred_directions",
        ["ai", "product"],
    )

    response = generate_semester_plan(
        PlanGenerateRequest(
            user_id="u_memory_plan",
            query="I want an AI applications semester.",
            term="Fall 2026",
        ),
        memory_service=memory_service,
    )

    assert [plan.label for plan in response.plans] == ["balanced", "ambitious", "conservative"]
    assert all("CS330" not in plan.courses for plan in response.plans)
    assert any("CS340" in plan.courses for plan in response.plans)
