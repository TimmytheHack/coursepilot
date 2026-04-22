"""Offline evaluation runner for CoursePilot planning behavior."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from app.eval.metrics import summarize_eval_results
from app.models.schemas import EvalRunResponse, PlanGenerateRequest, PlanningResponse
from app.services.planning_service import generate_semester_plan
from app.tools.catalog import load_course_catalog_by_id
from app.tools.graduation_checker import graduation_checker
from app.tools.prerequisite_checker import prerequisite_checker
from app.tools.schedule_conflict_checker import schedule_conflict_checker

CASES_PATH = Path(__file__).resolve().with_name("cases.jsonl")
REPORTS_DIR = Path(__file__).resolve().with_name("reports")


def _load_cases(cases_path: Path | None = None) -> list[dict[str, Any]]:
    """Load JSONL evaluation cases."""
    path = cases_path or CASES_PATH
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            cases.append(json.loads(stripped))
    return cases


def _report_path(run_id: str, reports_dir: Path | None = None) -> Path:
    """Build the report path for one eval run."""
    directory = reports_dir or REPORTS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{run_id}.json"


def _evaluate_case(case: dict[str, Any], course_catalog: dict[str, dict[str, Any]], degree_requirements: dict[str, Any]) -> dict[str, Any]:
    """Execute one eval case against the current planner."""
    request_model = PlanGenerateRequest(**case["request"])
    response = generate_semester_plan(request_model)
    response = PlanningResponse.model_validate(response)

    prerequisite_valid_plans = 0
    conflict_free_plans = 0
    graduation_checked_plans = 0
    plan_summaries: list[dict[str, Any]] = []
    for plan in response.plans:
        prerequisite_results = prerequisite_checker(
            request_model.completed_courses,
            plan.courses,
            course_catalog,
        )
        conflicts = schedule_conflict_checker(plan.courses, request_model.term.split(" ", 1)[0], course_catalog)
        graduation_summary = graduation_checker(
            request_model.completed_courses,
            plan.courses,
            degree_requirements,
        )

        if all(result["satisfied"] for result in prerequisite_results):
            prerequisite_valid_plans += 1
        if not conflicts:
            conflict_free_plans += 1
        if graduation_summary:
            graduation_checked_plans += 1

        plan_summaries.append(
            {
                "label": plan.label,
                "courses": plan.courses,
                "total_credits": plan.total_credits,
                "validation_facts": plan.validation_facts,
            }
        )

    expectations = case.get("expectations", {})
    actual_labels = {plan.label for plan in response.plans}
    required_labels = set(expectations.get("required_labels", []))
    completed_courses = set(request_model.completed_courses)
    excludes_completed_courses = all(
        not completed_courses.intersection(plan.courses)
        for plan in response.plans
    )

    passed = (
        len(response.plans) >= expectations.get("min_plan_count", 1)
        and required_labels.issubset(actual_labels)
        and (
            not expectations.get("exclude_completed_courses", False)
            or excludes_completed_courses
        )
    )

    return {
        "case_id": case["case_id"],
        "status": "passed" if passed else "failed",
        "schema_valid": True,
        "trace_id": response.trace_id,
        "plans": plan_summaries,
        "prerequisite_valid_plans": prerequisite_valid_plans,
        "conflict_free_plans": conflict_free_plans,
        "graduation_checked_plans": graduation_checked_plans,
        "expectations_met": passed,
    }


def run_eval_suite(
    *,
    cases_path: Path | None = None,
    reports_dir: Path | None = None,
) -> EvalRunResponse:
    """Run the offline evaluation suite and write a machine-readable report."""
    run_id = f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    course_catalog = load_course_catalog_by_id()
    degree_requirements = json.loads(
        (Path(__file__).resolve().parents[2] / "data" / "degree_requirements.json").read_text(encoding="utf-8")
    )
    case_results = [
        _evaluate_case(case, course_catalog, degree_requirements)
        for case in _load_cases(cases_path)
    ]
    metrics = summarize_eval_results(case_results)
    report = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "cases": case_results,
    }
    report_path = _report_path(run_id, reports_dir)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return EvalRunResponse(
        run_id=run_id,
        status="completed",
        summary=f"Executed {len(case_results)} eval case(s) with case pass rate {metrics['case_pass_rate']:.2f}.",
        metrics=metrics,
        report_path=str(report_path),
    )
