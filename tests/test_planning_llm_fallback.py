"""Integration tests for optional LLM-assisted planning fallback behavior."""

from app.config import AppConfig
from app.models.schemas import PlanGenerateRequest
from app.services.llm_service import LLMService
from app.services.planning_service import generate_semester_plan


def test_generate_semester_plan_uses_valid_llm_candidate_for_variant() -> None:
    """Valid LLM suggestions should be used and still validated downstream."""

    def mock_transport(_request):
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        '{"plans": ['
                        '{"label": "balanced", "course_ids": ["CS220", "CS340"], '
                        '"rationale_summary": "Keeps the semester practical and AI-focused."}'
                        "]}",
                    ),
                }
            ]
        }

    llm_service = LLMService(
        config=AppConfig(
            llm_enabled=True,
            anthropic_api_key="test-key",
            anthropic_model="test-model",
        ),
        transport=mock_transport,
    )

    response = generate_semester_plan(
        PlanGenerateRequest(
            user_id="u_llm",
            query="I want a balanced AI applications semester.",
            term="Fall 2026",
            completed_courses=["CS101", "CS120", "CS201", "CS240", "CS330"],
            preferred_directions=["ai", "product"],
            max_courses=3,
            max_credits=12,
        ),
        llm_service=llm_service,
    )

    assert [plan.label for plan in response.plans] == ["balanced", "ambitious", "conservative"]
    assert response.plans[0].courses == ["CS220", "CS340"]
    assert "AI-focused" in response.plans[0].rationale


def test_generate_semester_plan_falls_back_when_llm_output_is_invalid() -> None:
    """Invalid LLM output should preserve deterministic planner behavior."""

    def mock_transport(_request):
        return {"content": [{"type": "text", "text": "invalid output"}]}

    llm_service = LLMService(
        config=AppConfig(
            llm_enabled=True,
            anthropic_api_key="test-key",
            anthropic_model="test-model",
        ),
        transport=mock_transport,
    )

    response = generate_semester_plan(
        PlanGenerateRequest(
            user_id="u_llm_fallback",
            query="I want a balanced AI applications semester.",
            term="Fall 2026",
            completed_courses=["CS101", "CS120", "CS201", "CS240", "CS330"],
            preferred_directions=["ai", "product"],
            max_courses=3,
            max_credits=12,
        ),
        llm_service=llm_service,
    )

    assert [plan.label for plan in response.plans] == ["balanced", "ambitious", "conservative"]
    assert response.plans[0].courses == ["CS220", "CS230", "CS340"]
