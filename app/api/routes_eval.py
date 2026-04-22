"""Placeholder evaluation routes for the CoursePilot backend."""

from fastapi import APIRouter

from app.models.schemas import EvalRunResponse

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run", response_model=EvalRunResponse)
def run_eval() -> EvalRunResponse:
    """Return a typed placeholder response for evaluation runs."""
    return EvalRunResponse(
        run_id="placeholder-eval-run",
        status="not_started",
        summary="Evaluation pipeline has not been implemented yet.",
    )
