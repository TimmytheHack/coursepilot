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
                        "mode": "generate",
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


def test_run_eval_suite_supports_refine_cases_and_graceful_failures(tmp_path) -> None:
    """The eval runner should report refinement flags and graceful failures."""
    cases_path = tmp_path / "refine-cases.jsonl"
    cases_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "case_id": "refine_keep_swap",
                        "mode": "refine",
                        "request": {
                            "user_id": "u_eval_refine",
                            "prior_plan": {
                                "plan_id": "plan_ambitious",
                                "query": "I want an AI applications semester.",
                                "term": "Fall 2026",
                                "courses": ["CS210", "CS310", "CS340"],
                                "completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"],
                                "preferred_directions": ["ai", "product"],
                                "max_courses": 3,
                                "max_credits": 12,
                            },
                            "query": "Keep CS340 but replace CS310 with something lighter.",
                        },
                        "expectations": {
                            "min_plan_count": 1,
                            "required_labels": ["refined"],
                            "expected_kept_courses": ["CS340"],
                            "expected_removed_courses": ["CS310"],
                            "refinement_applied": True,
                            "memory_written": True,
                        },
                    }
                ),
                json.dumps(
                    {
                        "case_id": "refine_vague",
                        "mode": "refine",
                        "request": {
                            "user_id": "u_eval_refine",
                            "prior_plan": {
                                "plan_id": "plan_ambitious",
                                "query": "I want an AI applications semester.",
                                "term": "Fall 2026",
                                "courses": ["CS210", "CS310", "CS340"],
                                "completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"],
                                "preferred_directions": ["ai", "product"],
                                "max_courses": 3,
                                "max_credits": 12,
                            },
                            "query": "Change it.",
                        },
                        "expectations": {
                            "graceful_failure": True,
                            "error_contains": "too vague",
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    response = run_eval_suite(cases_path=cases_path, reports_dir=tmp_path / "reports")
    report = json.loads((tmp_path / "reports" / f"{response.run_id}.json").read_text(encoding="utf-8"))
    success_case, failure_case = report["cases"]

    assert response.status == "completed"
    assert response.metrics["refine_case_count"] == 2.0
    assert response.metrics["graceful_failure_rate"] == 0.5
    assert response.metrics["refinement_applied_rate"] == 0.5
    assert response.metrics["memory_written_rate"] == 0.5
    assert success_case["status"] == "passed"
    assert success_case["requested_keep_respected"] is True
    assert success_case["requested_remove_respected"] is True
    assert success_case["memory_written"] is True
    assert failure_case["status"] == "passed"
    assert failure_case["execution_status"] == "graceful_failure"
    assert "too vague" in failure_case["error_detail"]


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
    assert report["metrics"]["case_count"] == 4.0
    assert report["metrics"]["refine_case_count"] == 2.0
    assert report["metrics"]["case_pass_rate"] == 1.0
    assert [case["case_id"] for case in report["cases"]] == [
        "eval_case_bu_sample_ai_focus",
        "eval_case_bu_sample_refine_advanced_ai",
        "eval_case_bu_sample_search_agentic_ai",
        "eval_case_bu_sample_limited_refine_reduce_theory",
    ]
    assert all(case["status"] == "passed" for case in report["cases"])

    generate_case = report["cases"][0]
    refine_case = report["cases"][1]
    search_case = report["cases"][2]
    limitation_case = report["cases"][3]

    assert [plan["label"] for plan in generate_case["plans"]] == ["balanced", "ambitious", "conservative"]
    planned_courses = {
        course_id
        for plan in generate_case["plans"]
        for course_id in plan["courses"]
    }
    assert "CS598_AGENTIC_AI" in planned_courses
    assert "CS599_ADV_NLP" in planned_courses
    assert refine_case["plans"][0]["courses"] == ["CS599_ADV_NLP", "CS598_AGENTIC_AI"]
    assert search_case["search_results"][:2] == [
        {"course_id": "CS598_AGENTIC_AI", "title": "Agentic AI for Everything"},
        {"course_id": "CS599_ADV_NLP", "title": "Advanced Natural Language Processing"},
    ]
    assert limitation_case["execution_status"] == "graceful_failure"
    assert "No validated refinement" in limitation_case["error_detail"]
