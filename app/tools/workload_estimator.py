"""Deterministic workload estimation for planned courses."""

from __future__ import annotations

from typing import Any


def _workload_label(total_workload: int) -> str:
    """Map aggregate workload to a simple planning label."""
    if total_workload <= 8:
        return "light"
    if total_workload <= 14:
        return "balanced"
    return "heavy"


def workload_estimator(
    planned_courses: list[str],
    course_catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Estimate aggregate credit, workload, and difficulty for planned courses."""
    missing_course_ids = [course_id for course_id in planned_courses if course_id not in course_catalog]
    if missing_course_ids:
        missing_list = ", ".join(sorted(missing_course_ids))
        raise ValueError(f"Unknown planned course IDs: {missing_list}")

    total_credits = 0
    total_workload = 0
    total_difficulty = 0
    for course_id in planned_courses:
        course = course_catalog[course_id]
        total_credits += int(course["credits"])
        total_workload += int(course["workload"])
        total_difficulty += int(course["difficulty"])

    course_count = len(planned_courses)
    average_workload = total_workload / course_count if course_count else 0.0
    average_difficulty = total_difficulty / course_count if course_count else 0.0

    return {
        "planned_course_ids": planned_courses,
        "total_credits": total_credits,
        "total_workload": total_workload,
        "total_difficulty": total_difficulty,
        "average_workload": round(average_workload, 2),
        "average_difficulty": round(average_difficulty, 2),
        "workload_label": _workload_label(total_workload),
    }
