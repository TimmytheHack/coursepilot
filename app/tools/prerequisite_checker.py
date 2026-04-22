"""Deterministic prerequisite validation for planned courses."""

from __future__ import annotations

from typing import Any


def prerequisite_checker(
    completed_courses: list[str],
    target_courses: list[str],
    course_catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return structured prerequisite satisfaction results for each target course."""
    missing_course_ids = [course_id for course_id in target_courses if course_id not in course_catalog]
    if missing_course_ids:
        missing_list = ", ".join(sorted(missing_course_ids))
        raise ValueError(f"Unknown target course IDs: {missing_list}")

    completed_set = set(completed_courses)
    results: list[dict[str, Any]] = []
    for course_id in target_courses:
        prerequisites = course_catalog[course_id].get("prerequisites", [])
        missing_prerequisites = sorted(
            prerequisite
            for prerequisite in prerequisites
            if prerequisite not in completed_set
        )
        results.append(
            {
                "course_id": course_id,
                "satisfied": not missing_prerequisites,
                "missing": missing_prerequisites,
            }
        )

    return results
