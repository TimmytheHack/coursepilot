"""Prompt builders for optional LLM-assisted planner steps."""

from __future__ import annotations

import json


def build_candidate_plan_prompt(
    *,
    query: str,
    term: str,
    completed_courses: list[str],
    preferred_directions: list[str],
    max_courses: int,
    max_credits: int,
    available_courses: list[dict[str, object]],
) -> str:
    """Build a strict JSON-only prompt for candidate plan suggestions."""
    return (
        "You are assisting CoursePilot with candidate semester plan generation.\n"
        "Return only JSON with this shape:\n"
        "{\n"
        '  "plans": [\n'
        "    {\n"
        '      "label": "balanced|ambitious|conservative",\n'
        '      "course_ids": ["CS220", "CS340"],\n'
        '      "rationale_summary": "one short sentence"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Rules:\n"
        "- Use only course_ids listed in available_courses.\n"
        "- Do not include completed_courses.\n"
        f"- Use at most {max_courses} courses.\n"
        f"- Keep total credits at or below {max_credits}.\n"
        "- Include only the labels balanced, ambitious, or conservative.\n"
        "- Do not invent courses, prerequisites, schedules, or requirement claims.\n\n"
        f"query: {query}\n"
        f"term: {term}\n"
        f"completed_courses: {json.dumps(completed_courses)}\n"
        f"preferred_directions: {json.dumps(preferred_directions)}\n"
        f"available_courses: {json.dumps(available_courses)}\n"
    )
