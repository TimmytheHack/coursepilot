"""Unit tests for graduation and workload estimation tools."""

import json
from pathlib import Path

import pytest

from app.tools.catalog import load_course_catalog_by_id
from app.tools.graduation_checker import graduation_checker
from app.tools.workload_estimator import workload_estimator

COURSE_CATALOG = load_course_catalog_by_id()
DEGREE_REQUIREMENTS_PATH = Path(__file__).resolve().parents[1] / "data" / "degree_requirements.json"
DEGREE_REQUIREMENTS = json.loads(DEGREE_REQUIREMENTS_PATH.read_text(encoding="utf-8"))


def test_graduation_checker_reports_before_and_after_requirement_progress() -> None:
    """Requirement progress should reflect both completed and planned courses."""
    result = graduation_checker(
        completed_courses=["CS101", "CS120", "CS201"],
        planned_courses=["CS210", "CS220"],
        degree_requirements=DEGREE_REQUIREMENTS,
    )

    core_requirement = result["requirements"][0]

    assert result["program_name"] == "CoursePilot Sample Computing Major"
    assert core_requirement["completed_count"] == 3
    assert core_requirement["planned_count"] == 2
    assert core_requirement["satisfied_before"] is False
    assert core_requirement["satisfied_after"] is True


def test_graduation_checker_reports_remaining_depth_requirement() -> None:
    """Category-like elective requirements should expose remaining progress."""
    result = graduation_checker(
        completed_courses=["CS230"],
        planned_courses=["CS320"],
        degree_requirements=DEGREE_REQUIREMENTS,
    )

    depth_requirement = result["requirements"][1]

    assert depth_requirement["matching_completed_courses"] == ["CS230"]
    assert depth_requirement["matching_planned_courses"] == ["CS320"]
    assert depth_requirement["remaining_count_after_plan"] == 0
    assert depth_requirement["satisfied_after"] is True


def test_workload_estimator_summarizes_course_load() -> None:
    """Workload estimates should aggregate the selected course set."""
    result = workload_estimator(["CS210", "CS220", "CS380"], COURSE_CATALOG)

    assert result == {
        "planned_course_ids": ["CS210", "CS220", "CS380"],
        "total_credits": 12,
        "total_workload": 10,
        "total_difficulty": 9,
        "average_workload": 3.33,
        "average_difficulty": 3.0,
        "workload_label": "balanced",
    }


def test_workload_estimator_rejects_unknown_course_ids() -> None:
    """Unknown planned courses should fail loudly."""
    with pytest.raises(ValueError, match="Unknown planned course IDs: CS999"):
        workload_estimator(["CS210", "CS999"], COURSE_CATALOG)
