"""Tests for the offline evaluation runner."""

import json

from app.eval.runner import run_eval_suite


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
