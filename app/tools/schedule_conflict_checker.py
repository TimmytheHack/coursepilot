"""Deterministic schedule conflict validation for planned courses."""

from __future__ import annotations

from itertools import combinations
from typing import Any


def _time_overlaps(
    first_start: str,
    first_end: str,
    second_start: str,
    second_end: str,
) -> tuple[bool, str, str]:
    """Determine whether two time ranges overlap."""
    overlap_start = max(first_start, second_start)
    overlap_end = min(first_end, second_end)
    return overlap_start < overlap_end, overlap_start, overlap_end


def schedule_conflict_checker(
    planned_courses: list[str],
    term: str,
    course_catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return structured conflicts for overlapping course meeting times."""
    missing_course_ids = [course_id for course_id in planned_courses if course_id not in course_catalog]
    if missing_course_ids:
        missing_list = ", ".join(sorted(missing_course_ids))
        raise ValueError(f"Unknown planned course IDs: {missing_list}")

    conflicts: list[dict[str, Any]] = []
    for first_course_id, second_course_id in combinations(planned_courses, 2):
        first_slots = course_catalog[first_course_id].get("time_slots", [])
        second_slots = course_catalog[second_course_id].get("time_slots", [])

        for first_slot in first_slots:
            if first_slot.get("term") != term:
                continue
            for second_slot in second_slots:
                if second_slot.get("term") != term:
                    continue

                shared_days = sorted(set(first_slot["days"]).intersection(second_slot["days"]))
                if not shared_days:
                    continue

                overlaps, overlap_start, overlap_end = _time_overlaps(
                    first_slot["start"],
                    first_slot["end"],
                    second_slot["start"],
                    second_slot["end"],
                )
                if not overlaps:
                    continue

                conflicts.append(
                    {
                        "course_ids": [first_course_id, second_course_id],
                        "term": term,
                        "days": shared_days,
                        "overlap_start": overlap_start,
                        "overlap_end": overlap_end,
                    }
                )

    return conflicts
