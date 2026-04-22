"""Tests for the optional Anthropic-backed LLM service."""

from app.config import AppConfig
from app.services.llm_service import LLMService


def test_llm_service_parses_valid_candidate_plan_output() -> None:
    """The LLM service should parse valid JSON candidate plans."""

    def mock_transport(_request):
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        '{"plans": [{"label": "balanced", "course_ids": ["CS220", "CS340"], '
                        '"rationale_summary": "Focuses on applied AI with a moderate load."}]}'
                    ),
                }
            ]
        }

    service = LLMService(
        config=AppConfig(
            llm_enabled=True,
            anthropic_api_key="test-key",
            anthropic_model="test-model",
        ),
        transport=mock_transport,
    )

    plans = service.suggest_candidate_plans(
        query="I want an AI applications semester.",
        term="Fall 2026",
        completed_courses=["CS101"],
        preferred_directions=["ai", "product"],
        max_courses=3,
        max_credits=12,
        available_courses=[
            {"course_id": "CS220", "title": "Web Application Engineering"},
            {"course_id": "CS340", "title": "Applied Machine Learning"},
        ],
    )

    assert plans is not None
    assert plans[0].label == "balanced"
    assert plans[0].course_ids == ["CS220", "CS340"]


def test_llm_service_returns_none_for_invalid_output() -> None:
    """Invalid model output should trigger deterministic fallback."""

    def mock_transport(_request):
        return {"content": [{"type": "text", "text": "not valid json"}]}

    service = LLMService(
        config=AppConfig(
            llm_enabled=True,
            anthropic_api_key="test-key",
            anthropic_model="test-model",
        ),
        transport=mock_transport,
    )

    plans = service.suggest_candidate_plans(
        query="I want an AI applications semester.",
        term="Fall 2026",
        completed_courses=["CS101"],
        preferred_directions=["ai", "product"],
        max_courses=3,
        max_credits=12,
        available_courses=[
            {"course_id": "CS220", "title": "Web Application Engineering"},
            {"course_id": "CS340", "title": "Applied Machine Learning"},
        ],
    )

    assert plans is None
