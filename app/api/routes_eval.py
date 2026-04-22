"""Evaluation routes for the CoursePilot backend."""

from fastapi import APIRouter

from app.eval.runner import run_eval_suite
from app.models.schemas import EvalRunResponse

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/run", response_model=EvalRunResponse)
def run_eval() -> EvalRunResponse:
    """Run the offline evaluation suite and return a summary."""
    return run_eval_suite()
