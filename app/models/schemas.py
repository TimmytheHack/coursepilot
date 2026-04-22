"""Typed API schemas for the CoursePilot backend."""

from pydantic import BaseModel, Field


class PlanGenerateRequest(BaseModel):
    """Request payload for initial plan generation."""

    user_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    term: str = Field(..., min_length=1)


class PlanRefineRequest(BaseModel):
    """Request payload for plan refinement."""

    user_id: str = Field(..., min_length=1)
    previous_plan_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)


class CoursePlan(BaseModel):
    """Structured course plan response object."""

    label: str
    courses: list[str]
    total_credits: int = Field(..., ge=0)
    rationale: str
    risks: list[str]
    fit_score: float = Field(..., ge=0.0, le=1.0)


class PlanningResponse(BaseModel):
    """Response contract for generated or refined plans."""

    trace_id: str
    plans: list[CoursePlan]
    summary: str
    next_actions: list[str]


class CourseSearchResult(BaseModel):
    """Placeholder course search result object."""

    course_id: str
    title: str
    match_reason: str


class CourseSearchResponse(BaseModel):
    """Response contract for course search."""

    query: str
    results: list[CourseSearchResult]


class EvalRunResponse(BaseModel):
    """Response contract for evaluation runs."""

    run_id: str
    status: str
    summary: str


class ErrorResponse(BaseModel):
    """Generic error response contract."""

    detail: str
