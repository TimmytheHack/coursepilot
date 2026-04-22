"""Typed API schemas for the CoursePilot backend."""

from typing import Optional

from pydantic import BaseModel, Field


class PlanGenerateRequest(BaseModel):
    """Request payload for initial plan generation."""

    user_id: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    term: str = Field(..., min_length=1)
    completed_courses: list[str] = Field(default_factory=list)
    preferred_directions: list[str] = Field(default_factory=list)
    max_courses: int = Field(3, ge=1, le=6)
    max_credits: int = Field(16, ge=1)
    avoid_morning_classes: bool = False


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
    validation_facts: list[str]
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
    metrics: dict[str, float] = Field(default_factory=dict)
    report_path: Optional[str] = None


class ErrorResponse(BaseModel):
    """Generic error response contract."""

    detail: str
