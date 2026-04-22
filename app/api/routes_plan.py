"""Planning routes for the CoursePilot backend."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import PlanningResponse, PlanGenerateRequest, PlanRefineRequest
from app.services.planning_service import generate_semester_plan
from app.services.refinement_service import refine_semester_plan

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/generate", response_model=PlanningResponse)
def generate_plan(payload: PlanGenerateRequest) -> PlanningResponse:
    """Return validated deterministic candidate plans."""
    try:
        return generate_semester_plan(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/refine", response_model=PlanningResponse)
def refine_plan(payload: PlanRefineRequest) -> PlanningResponse:
    """Return one validated deterministic refinement for a prior plan."""
    try:
        return refine_semester_plan(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
