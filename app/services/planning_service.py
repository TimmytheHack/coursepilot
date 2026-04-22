"""Service wrapper around the deterministic planner graph."""

from __future__ import annotations

from app.agents.planner_graph import run_planner_graph
from app.models.schemas import PlanGenerateRequest, PlanningResponse
from app.services.memory_service import MemoryService


def generate_semester_plan(
    request: PlanGenerateRequest,
    memory_service: MemoryService | None = None,
) -> PlanningResponse:
    """Generate deterministic candidate semester plans via the planner graph."""
    return run_planner_graph(request, memory_service=memory_service)
