"""Unit tests for prerequisite and schedule validation tools."""

import pytest

from app.tools.catalog import load_course_catalog_by_id
from app.tools.prerequisite_checker import prerequisite_checker
from app.tools.schedule_conflict_checker import schedule_conflict_checker


COURSE_CATALOG = load_course_catalog_by_id()


def test_prerequisite_checker_marks_satisfied_courses() -> None:
    """Completed prerequisites should satisfy the target course requirements."""
    results = prerequisite_checker(["CS101"], ["CS201"], COURSE_CATALOG)

    assert results == [{"course_id": "CS201", "satisfied": True, "missing": []}]


def test_prerequisite_checker_reports_missing_courses() -> None:
    """Missing prerequisites should be surfaced explicitly."""
    results = prerequisite_checker(["CS201"], ["CS330"], COURSE_CATALOG)

    assert results == [{"course_id": "CS330", "satisfied": False, "missing": ["CS240"]}]


def test_prerequisite_checker_rejects_unknown_course_ids() -> None:
    """Unknown target courses should fail loudly."""
    with pytest.raises(ValueError, match="Unknown target course IDs: CS999"):
        prerequisite_checker(["CS101"], ["CS999"], COURSE_CATALOG)


def test_schedule_conflict_checker_detects_overlapping_slots() -> None:
    """Overlapping courses in the same term should be reported structurally."""
    conflicts = schedule_conflict_checker(["CS310", "CS410"], "Fall", COURSE_CATALOG)

    assert conflicts == [
        {
            "course_ids": ["CS310", "CS410"],
            "term": "Fall",
            "days": ["Mon", "Wed"],
            "overlap_start": "13:00",
            "overlap_end": "13:45",
        }
    ]


def test_schedule_conflict_checker_returns_empty_for_non_overlapping_courses() -> None:
    """Courses without overlapping slots should return no conflicts."""
    conflicts = schedule_conflict_checker(["CS101", "CS220"], "Fall", COURSE_CATALOG)

    assert conflicts == []


def test_schedule_conflict_checker_rejects_unknown_course_ids() -> None:
    """Unknown planned course IDs should fail loudly."""
    with pytest.raises(ValueError, match="Unknown planned course IDs: CS999"):
        schedule_conflict_checker(["CS101", "CS999"], "Fall", COURSE_CATALOG)
