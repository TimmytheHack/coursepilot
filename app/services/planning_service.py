"""Service wrapper around the deterministic planner graph."""

from __future__ import annotations

from app.agents.planner_graph import run_planner_graph
from app.models.schemas import PlanGenerateRequest, PlanningResponse
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService


def generate_semester_plan(
    request: PlanGenerateRequest,
    memory_service: MemoryService | None = None,
    llm_service: LLMService | None = None,
    course_catalog: list[dict[str, object]] | None = None,
    course_catalog_by_id: dict[str, dict[str, object]] | None = None,
    degree_requirements: dict[str, object] | None = None,
    required_course_ids: list[str] | None = None,
    excluded_course_ids: list[str] | None = None,
) -> PlanningResponse:
    """Generate deterministic candidate semester plans via the planner graph."""
    return run_planner_graph(
        request,
        memory_service=memory_service,
        llm_service=llm_service,
        course_catalog=course_catalog,
        course_catalog_by_id=course_catalog_by_id,
        degree_requirements=degree_requirements,
        required_course_ids=required_course_ids,
        excluded_course_ids=excluded_course_ids,
    )
