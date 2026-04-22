"""Placeholder planning routes for the CoursePilot backend."""

from fastapi import APIRouter

from app.models.schemas import CoursePlan, PlanningResponse, PlanGenerateRequest, PlanRefineRequest

router = APIRouter(prefix="/plan", tags=["plan"])


def _build_placeholder_plan(label: str) -> CoursePlan:
    """Create a stable placeholder plan for schema validation."""
    return CoursePlan(
        label=label,
        courses=["CS000"],
        total_credits=4,
        rationale="Placeholder response until planning logic is implemented.",
        risks=["Planning service not implemented yet."],
        fit_score=0.5,
    )


@router.post("/generate", response_model=PlanningResponse)
def generate_plan(payload: PlanGenerateRequest) -> PlanningResponse:
    """Return a typed placeholder response for initial plan generation."""
    return PlanningResponse(
        trace_id=f"placeholder-generate-{payload.user_id}",
        plans=[_build_placeholder_plan("balanced-placeholder")],
        summary=f"Placeholder plan generated for {payload.term}.",
        next_actions=["Implement deterministic planning service."],
    )


@router.post("/refine", response_model=PlanningResponse)
def refine_plan(payload: PlanRefineRequest) -> PlanningResponse:
    """Return a typed placeholder response for plan refinement."""
    return PlanningResponse(
        trace_id=f"placeholder-refine-{payload.user_id}",
        plans=[_build_placeholder_plan("refined-placeholder")],
        summary=f"Placeholder refinement created from {payload.previous_plan_id}.",
        next_actions=["Implement plan revision logic."],
    )
