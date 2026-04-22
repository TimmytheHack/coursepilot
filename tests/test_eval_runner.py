"""Tests for the offline evaluation runner."""

import json
from pathlib import Path

from app.eval.runner import run_eval_suite


BU_SAMPLE_CASES_PATH = Path(__file__).resolve().parents[1] / "app" / "eval" / "cases_bu_sample.jsonl"


def test_run_eval_suite_generates_machine_readable_report(tmp_path) -> None:
    """The eval runner should execute cases and write a report."""
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "case_id": "case_one",
                        "request": {
                            "user_id": "u_eval",
                            "query": "I want a balanced AI applications semester.",
                            "term": "Fall 2026",
                            "completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"],
                            "preferred_directions": ["ai", "product"],
                            "max_courses": 3,
                            "max_credits": 12,
                        },
                        "expectations": {
                            "min_plan_count": 2,
                            "required_labels": ["balanced", "ambitious"],
                            "exclude_completed_courses": True,
                        },
                    }
                )
            ]
        ),
        encoding="utf-8",
    )

    response = run_eval_suite(cases_path=cases_path, reports_dir=tmp_path / "reports")
    report = json.loads((tmp_path / "reports" / f"{response.run_id}.json").read_text(encoding="utf-8"))

    assert response.status == "completed"
    assert response.metrics["schema_success_rate"] == 1.0
    assert response.metrics["case_pass_rate"] == 1.0
    assert report["run_id"] == response.run_id
    assert report["cases"][0]["status"] == "passed"


def test_run_eval_suite_supports_bu_sample_catalog_fixture(tmp_path) -> None:
    """The eval runner should support the imported BU sample as an explicit catalog."""
    response = run_eval_suite(
        cases_path=BU_SAMPLE_CASES_PATH,
        reports_dir=tmp_path / "reports",
        catalog_id="bu_sample",
    )
    report = json.loads((tmp_path / "reports" / f"{response.run_id}.json").read_text(encoding="utf-8"))

    assert response.status == "completed"
    assert report["catalog_id"] == "bu_sample"
    assert report["cases"][0]["status"] == "passed"
    assert [plan["label"] for plan in report["cases"][0]["plans"]] == ["balanced", "ambitious", "conservative"]
    planned_courses = {
        course_id
        for plan in report["cases"][0]["plans"]
        for course_id in plan["courses"]
    }
    assert "CS598_AGENTIC_AI" in planned_courses
    assert "CS599_ADV_NLP" in planned_courses
