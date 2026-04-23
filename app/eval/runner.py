"""Offline evaluation runner for CoursePilot planning behavior."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from typing import Any

from app.eval.metrics import summarize_eval_results
from app.models.schemas import EvalRunResponse, PlanGenerateRequest, PlanRefineRequest, PlanningResponse
from app.services.memory_service import MemoryService
from app.services.planning_service import generate_semester_plan
from app.services.refinement_service import refine_semester_plan
from app.tools.catalog import DEFAULT_CATALOG_ID, load_catalog, load_catalog_by_id
from app.tools.course_search import course_search_in_catalog
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


def _prime_memory_service(
    memory_service: MemoryService,
    user_id: str,
    memory_setup: dict[str, Any] | None,
) -> None:
    """Seed one eval-local memory service with explicit profile and entries."""
    if not memory_setup:
        return

    profile = memory_setup.get("profile")
    if profile:
        memory_service.save_user_profile(user_id, profile)

    for entry in memory_setup.get("entries", []):
        memory_service.upsert_memory(
            user_id,
            entry["memory_type"],
            entry["key"],
            entry["value"],
        )


def _summarize_response(
    response: PlanningResponse,
    *,
    completed_courses: list[str],
    term: str,
    course_catalog_by_id: dict[str, dict[str, Any]],
    degree_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Build per-plan validation summaries shared by generate and refine evals."""
    prerequisite_valid_plans = 0
    conflict_free_plans = 0
    graduation_checked_plans = 0
    plan_summaries: list[dict[str, Any]] = []
    season = term.split(" ", 1)[0]

    for plan in response.plans:
        prerequisite_results = prerequisite_checker(
            completed_courses,
            plan.courses,
            course_catalog_by_id,
        )
        conflicts = schedule_conflict_checker(plan.courses, season, course_catalog_by_id)
        graduation_summary = graduation_checker(
            completed_courses,
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

    return {
        "prerequisite_valid_plans": prerequisite_valid_plans,
        "conflict_free_plans": conflict_free_plans,
        "graduation_checked_plans": graduation_checked_plans,
        "plans": plan_summaries,
    }


def _evaluate_generate_expectations(
    expectations: dict[str, Any],
    response: PlanningResponse,
    completed_courses: list[str],
) -> tuple[bool, dict[str, Any]]:
    """Evaluate generate-mode case expectations against one planning response."""
    actual_labels = {plan.label for plan in response.plans}
    required_labels = set(expectations.get("required_labels", []))
    completed_course_set = set(completed_courses)
    excludes_completed_courses = all(
        not completed_course_set.intersection(plan.courses)
        for plan in response.plans
    )

    required_courses = set(expectations.get("required_courses", []))
    forbidden_courses = set(expectations.get("forbidden_courses", []))
    required_courses_present = required_courses.issubset(
        {course_id for plan in response.plans for course_id in plan.courses}
    )
    forbidden_courses_absent = not forbidden_courses.intersection(
        {course_id for plan in response.plans for course_id in plan.courses}
    )

    passed = (
        len(response.plans) >= expectations.get("min_plan_count", 1)
        and required_labels.issubset(actual_labels)
        and (
            not expectations.get("exclude_completed_courses", False)
            or excludes_completed_courses
        )
        and (not required_courses or required_courses_present)
        and (not forbidden_courses or forbidden_courses_absent)
    )

    return passed, {
        "required_courses_present": required_courses_present,
        "forbidden_courses_absent": forbidden_courses_absent,
    }


def _evaluate_refine_expectations(
    expectations: dict[str, Any],
    response: PlanningResponse | None,
    error_detail: str | None,
    *,
    prior_plan_courses: list[str],
    memory_written: bool,
) -> tuple[bool, dict[str, Any]]:
    """Evaluate refine-mode expectations against one response or graceful failure."""
    graceful_failure = error_detail is not None

    if response is None:
        actual_labels: set[str] = set()
        required_labels = set(expectations.get("required_labels", []))
        expected_graceful_failure = expectations.get("graceful_failure")
        error_contains = expectations.get("error_contains")
        passed = (
            expected_graceful_failure is True
            and not required_labels
            and (
                error_contains is None
                or error_contains.lower() in error_detail.lower()
            )
        )
        return passed, {
            "refinement_applied": False,
            "requested_keep_respected": False,
            "requested_remove_respected": False,
            "graceful_failure": graceful_failure,
            "memory_written": memory_written,
        }

    actual_labels = {plan.label for plan in response.plans}
    required_labels = set(expectations.get("required_labels", []))
    expected_kept_courses = set(expectations.get("expected_kept_courses", []))
    expected_removed_courses = set(expectations.get("expected_removed_courses", []))
    prior_course_set = set(prior_plan_courses)
    returned_course_sets = [set(plan.courses) for plan in response.plans]
    refinement_applied = any(plan_courses != prior_course_set for plan_courses in returned_course_sets)
    requested_keep_respected = all(
        expected_kept_courses.issubset(plan_courses) for plan_courses in returned_course_sets
    )
    requested_remove_respected = all(
        not expected_removed_courses.intersection(plan_courses)
        for plan_courses in returned_course_sets
    )
    max_total_credits = expectations.get("max_total_credits")
    credits_ok = max_total_credits is None or all(
        plan.total_credits <= max_total_credits for plan in response.plans
    )

    passed = (
        len(response.plans) >= expectations.get("min_plan_count", 1)
        and required_labels.issubset(actual_labels)
        and expectations.get("graceful_failure", False) is False
        and (
            "refinement_applied" not in expectations
            or refinement_applied is expectations["refinement_applied"]
        )
        and (
            not expected_kept_courses
            or requested_keep_respected
        )
        and (
            not expected_removed_courses
            or requested_remove_respected
        )
        and (
            "memory_written" not in expectations
            or memory_written is expectations["memory_written"]
        )
        and credits_ok
    )

    return passed, {
        "refinement_applied": refinement_applied,
        "requested_keep_respected": requested_keep_respected,
        "requested_remove_respected": requested_remove_respected,
        "graceful_failure": graceful_failure,
        "memory_written": memory_written,
    }


def _evaluate_search_expectations(
    expectations: dict[str, Any],
    search_results: list[dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    """Evaluate search-mode expectations against deterministic search results."""
    result_ids = [course["course_id"] for course in search_results]
    expected_top_result = expectations.get("expected_top_result")
    expected_contains_ids = set(expectations.get("expected_contains_ids", []))
    max_results = expectations.get("max_results")

    top_result_matches = expected_top_result is None or (
        bool(result_ids) and result_ids[0] == expected_top_result
    )
    contains_expected_ids = expected_contains_ids.issubset(set(result_ids))
    count_ok = max_results is None or len(result_ids) <= max_results

    passed = top_result_matches and contains_expected_ids and count_ok
    return passed, {
        "top_result_matches": top_result_matches,
        "contains_expected_ids": contains_expected_ids,
        "search_result_count": len(result_ids),
    }


def _evaluate_case(
    case: dict[str, Any],
    course_catalog: list[dict[str, Any]],
    course_catalog_by_id: dict[str, dict[str, Any]],
    degree_requirements: dict[str, Any],
) -> dict[str, Any]:
    """Execute one eval case against the current planner."""
    mode = case.get("mode", "generate")
    expectations = case.get("expectations", {})
    request_data = case["request"]

    with tempfile.TemporaryDirectory(prefix="coursepilot-eval-") as temp_dir:
        memory_service = MemoryService(db_path=Path(temp_dir) / f"{case['case_id']}.db")
        _prime_memory_service(
            memory_service,
            request_data["user_id"],
            case.get("memory_setup"),
        )
        before_entries = memory_service.get_memories(request_data["user_id"])

        response: PlanningResponse | None = None
        search_results: list[dict[str, Any]] = []
        trace_id: str | None = None
        error_detail: str | None = None
        completed_courses: list[str]
        term: str

        try:
            if mode == "refine":
                request_model = PlanRefineRequest(**request_data)
                response = refine_semester_plan(
                    request_model,
                    memory_service=memory_service,
                    course_catalog=course_catalog,
                    course_catalog_by_id=course_catalog_by_id,
                    degree_requirements=degree_requirements,
                )
                completed_courses = request_model.prior_plan.completed_courses
                term = request_model.prior_plan.term
                response = PlanningResponse.model_validate(response)
                trace_id = response.trace_id
            elif mode == "search":
                search_results = course_search_in_catalog(
                    request_data["query"],
                    request_data.get("preferred_directions", []),
                    course_catalog,
                    max_results=request_data.get("max_results", 10),
                )
                completed_courses = []
                term = request_data.get("term", "")
            else:
                request_model = PlanGenerateRequest(**request_data)
                response = generate_semester_plan(
                    request_model,
                    memory_service=memory_service,
                    course_catalog=course_catalog,
                    course_catalog_by_id=course_catalog_by_id,
                    degree_requirements=degree_requirements,
                )
                completed_courses = request_model.completed_courses
                term = request_model.term
                trace_id = response.trace_id
                response = PlanningResponse.model_validate(response)
        except ValueError as exc:
            error_detail = str(exc)
            if mode == "refine":
                request_model = PlanRefineRequest(**request_data)
                completed_courses = request_model.prior_plan.completed_courses
                term = request_model.prior_plan.term
                trace_id = f"refine-{request_model.user_id}-{request_model.prior_plan.term.lower().replace(' ', '-')}"
            elif mode == "search":
                completed_courses = []
                term = request_data.get("term", "")
            else:
                request_model = PlanGenerateRequest(**request_data)
                completed_courses = request_model.completed_courses
                term = request_model.term
        after_entries = memory_service.get_memories(request_data["user_id"])
        memory_written = after_entries != before_entries

    if mode == "search":
        search_results = [] if error_detail is not None else search_results
        passed, search_flags = _evaluate_search_expectations(expectations, search_results)
        execution_status = "graceful_failure" if error_detail is not None else "completed"
        return {
            "case_id": case["case_id"],
            "mode": mode,
            "status": "passed" if passed else "failed",
            "execution_status": execution_status,
            "schema_valid": error_detail is None,
            "trace_id": None,
            "plans": [],
            "prerequisite_valid_plans": 0,
            "conflict_free_plans": 0,
            "graduation_checked_plans": 0,
            "expectations_met": passed,
            "error_detail": error_detail,
            "search_results": [
                {
                    "course_id": course["course_id"],
                    "title": course["title"],
                }
                for course in search_results
            ],
            **search_flags,
        }

    if response is not None:
        shared_summary = _summarize_response(
            response,
            completed_courses=completed_courses,
            term=term,
            course_catalog_by_id=course_catalog_by_id,
            degree_requirements=degree_requirements,
        )
    else:
        shared_summary = {
            "prerequisite_valid_plans": 0,
            "conflict_free_plans": 0,
            "graduation_checked_plans": 0,
            "plans": [],
        }

    if mode == "refine":
        prior_plan_courses = request_data["prior_plan"]["courses"]
        passed, refine_flags = _evaluate_refine_expectations(
            expectations,
            response,
            error_detail,
            prior_plan_courses=prior_plan_courses,
            memory_written=memory_written,
        )
    else:
        passed, refine_flags = _evaluate_generate_expectations(
            expectations,
            response if response is not None else PlanningResponse(
                trace_id=trace_id or "",
                plans=[],
                summary="",
                next_actions=[],
            ),
            completed_courses,
        )

    execution_status = "graceful_failure" if error_detail is not None else "completed"
    return {
        "case_id": case["case_id"],
        "mode": mode,
        "status": "passed" if passed else "failed",
        "execution_status": execution_status,
        "schema_valid": error_detail is None,
        "trace_id": trace_id,
        "plans": shared_summary["plans"],
        "prerequisite_valid_plans": shared_summary["prerequisite_valid_plans"],
        "conflict_free_plans": shared_summary["conflict_free_plans"],
        "graduation_checked_plans": shared_summary["graduation_checked_plans"],
        "expectations_met": passed,
        "error_detail": error_detail,
        **refine_flags,
    }


def run_eval_suite(
    *,
    cases_path: Path | None = None,
    reports_dir: Path | None = None,
    catalog_id: str = DEFAULT_CATALOG_ID,
) -> EvalRunResponse:
    """Run the offline evaluation suite and write a machine-readable report."""
    run_id = f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    course_catalog = load_catalog(catalog_id)
    course_catalog_by_id = load_catalog_by_id(catalog_id)
    degree_requirements = json.loads(
        (Path(__file__).resolve().parents[2] / "data" / "degree_requirements.json").read_text(encoding="utf-8")
    )
    case_results = [
        _evaluate_case(case, course_catalog, course_catalog_by_id, degree_requirements)
        for case in _load_cases(cases_path)
    ]
    metrics = summarize_eval_results(case_results)
    report = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_id": catalog_id,
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
