"""Deterministic graduation progress checks for the sample program model."""

from __future__ import annotations

from typing import Any


def _matching_courses(
    requirement: dict[str, Any],
    completed_courses: set[str],
    planned_courses: set[str],
) -> tuple[list[str], list[str]]:
    """Return completed and planned courses that match a requirement."""
    qualifying_course_ids = requirement.get("course_ids") or requirement.get("qualifying_course_ids") or []
    qualifying_set = set(qualifying_course_ids)

    completed_matches = sorted(qualifying_set.intersection(completed_courses))
    planned_matches = sorted(qualifying_set.intersection(planned_courses) - set(completed_matches))
    return completed_matches, planned_matches


def graduation_checker(
    completed_courses: list[str],
    planned_courses: list[str],
    degree_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Report requirement and credit progress before and after planned courses."""
    completed_set = set(completed_courses)
    planned_set = set(planned_courses)
    major_credits_required = degree_requirements["major_credits_required"]

    requirement_results: list[dict[str, Any]] = []
    for requirement in degree_requirements["requirements"]:
        min_count = requirement["min_count"]
        completed_matches, planned_matches = _matching_courses(requirement, completed_set, planned_set)
        completed_count = len(completed_matches)
        planned_count = len(planned_matches)
        total_count = completed_count + planned_count

        requirement_results.append(
            {
                "requirement_id": requirement["requirement_id"],
                "name": requirement["name"],
                "min_count": min_count,
                "completed_count": completed_count,
                "planned_count": planned_count,
                "satisfied_before": completed_count >= min_count,
                "satisfied_after": total_count >= min_count,
                "matching_completed_courses": completed_matches,
                "matching_planned_courses": planned_matches,
                "remaining_count_after_plan": max(min_count - total_count, 0),
            }
        )

    completed_major_credits = len(completed_set) * 4
    planned_major_credits = len(planned_set - completed_set) * 4

    return {
        "program_name": degree_requirements["program_name"],
        "credit_progress": {
            "major_credits_required": major_credits_required,
            "completed_major_credits": completed_major_credits,
            "planned_major_credits": planned_major_credits,
            "major_credits_after_plan": completed_major_credits + planned_major_credits,
        },
        "requirements": requirement_results,
        "all_requirements_satisfied_before": all(
            requirement["satisfied_before"] for requirement in requirement_results
        ),
        "all_requirements_satisfied_after": all(
            requirement["satisfied_after"] for requirement in requirement_results
        ),
    }
