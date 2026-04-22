"""Typed state contracts for the deterministic planner graph."""

from __future__ import annotations

from typing import Any, TypedDict


class PlannerState(TypedDict, total=False):
    """State passed between deterministic planning nodes."""

    user_id: str
    query: str
    term: str
    completed_courses: list[str]
    preferred_directions: list[str]
    max_courses: int
    max_credits: int
    avoid_morning_classes: bool
    season: str
    user_profile: dict[str, Any]
    course_catalog: list[dict[str, Any]]
    course_catalog_by_id: dict[str, dict[str, Any]]
    degree_requirements: dict[str, Any]
    retrieved_courses: list[dict[str, Any]]
    candidate_plans: list[dict[str, Any]]
    validation_results: list[dict[str, Any]]
    final_response: dict[str, Any]
    trace: list[dict[str, Any]]
    messages: list[str]
    trace_id: str
    error: str | None
