"""Tests for deterministic plan refinement behavior."""

from app.models.schemas import PlanRefineRequest
from app.services.memory_service import MemoryService
from app.services.refinement_service import refine_semester_plan
from app.services.trace_service import TraceService
from app.tools.catalog import load_course_catalog_by_id


COURSE_CATALOG = load_course_catalog_by_id()


def _prior_plan_context() -> dict[str, object]:
    """Build a stable prior plan context for refinement tests."""
    return {
        "plan_id": "plan_ambitious",
        "query": "I want an AI applications semester.",
        "term": "Fall 2026",
        "courses": ["CS210", "CS310", "CS340"],
        "completed_courses": ["CS101", "CS120", "CS201", "CS240", "CS330"],
        "preferred_directions": ["ai", "product"],
        "max_courses": 3,
        "max_credits": 12,
    }


def test_refine_semester_plan_keeps_named_course_and_replaces_explicit_course(tmp_path) -> None:
    """Refinement should preserve a named course and remove an explicitly rejected one."""
    memory_service = MemoryService(db_path=tmp_path / "refine.db")
    trace_service = TraceService()

    response = refine_semester_plan(
        PlanRefineRequest(
            user_id="u_refine_keep_swap",
            prior_plan=_prior_plan_context(),
            query="Keep CS340 but replace CS310 with something lighter.",
        ),
        memory_service=memory_service,
        trace_service=trace_service,
    )

    plan = response.plans[0]
    trace = trace_service.get_trace(response.trace_id)
    rejected_courses = memory_service.load_user_context("u_refine_keep_swap")["rejected_courses"]

    assert response.trace_id == "refine-u_refine_keep_swap-fall-2026"
    assert len(response.plans) == 1
    assert plan.label == "refined"
    assert "CS340" in plan.courses
    assert "CS310" not in plan.courses
    assert plan.validation_facts
    assert rejected_courses == {"CS310": "Keep CS340 but replace CS310 with something lighter."}
    assert trace is not None
    assert [stage["stage"] for stage in trace["stages"]] == [
        "parse_refinement_intent",
        "derive_refinement_constraints",
        "rerun_planner_with_constraints",
        "select_refined_plan",
        "persist_refinement_feedback",
    ]


def test_refine_semester_plan_supports_course_titles(tmp_path) -> None:
    """Refinement should resolve exact course-title references conservatively."""
    memory_service = MemoryService(db_path=tmp_path / "refine-title.db")

    response = refine_semester_plan(
        PlanRefineRequest(
            user_id="u_refine_title",
            prior_plan=_prior_plan_context(),
            query="Keep Applied Machine Learning but replace Algorithms with something lighter.",
        ),
        memory_service=memory_service,
    )

    plan = response.plans[0]

    assert len(response.plans) == 1
    assert "CS340" in plan.courses
    assert "CS310" not in plan.courses


def test_refine_semester_plan_makes_plan_lighter(tmp_path) -> None:
    """Refinement should reduce deterministic workload when asked for a lighter plan."""
    memory_service = MemoryService(db_path=tmp_path / "refine-lighter.db")

    response = refine_semester_plan(
        PlanRefineRequest(
            user_id="u_refine_lighter",
            prior_plan=_prior_plan_context(),
            query="Make this lighter.",
        ),
        memory_service=memory_service,
    )

    prior_workload = sum(COURSE_CATALOG[course_id]["workload"] for course_id in _prior_plan_context()["courses"])
    refined_workload = sum(COURSE_CATALOG[course_id]["workload"] for course_id in response.plans[0].courses)

    assert len(response.plans) == 1
    assert response.plans[0].total_credits <= 8
    assert refined_workload < prior_workload


def test_refine_semester_plan_rejects_ambiguous_title_reference(tmp_path) -> None:
    """Refinement should fail clearly when a title fragment matches multiple prior courses."""
    memory_service = MemoryService(db_path=tmp_path / "refine-ambiguous.db")

    try:
        refine_semester_plan(
            PlanRefineRequest(
                user_id="u_refine_ambiguous",
                prior_plan={
                    "plan_id": "plan_ambiguous",
                    "query": "I want a machine learning semester.",
                    "term": "Spring 2026",
                    "courses": ["CS330", "CS340", "CS230"],
                    "completed_courses": ["CS101", "CS120", "CS201", "CS240"],
                    "preferred_directions": ["ai"],
                    "max_courses": 3,
                    "max_credits": 12,
                },
                query="Keep Machine Learning but replace Data Management.",
            ),
            memory_service=memory_service,
        )
    except ValueError as exc:
        assert "ambiguous" in str(exc)
    else:
        raise AssertionError("Expected refinement to reject the ambiguous title reference.")


def test_refine_semester_plan_rejects_unknown_title_reference(tmp_path) -> None:
    """Refinement should fail clearly when a title resolves outside the prior plan."""
    memory_service = MemoryService(db_path=tmp_path / "refine-title-miss.db")

    try:
        refine_semester_plan(
            PlanRefineRequest(
                user_id="u_refine_title_miss",
                prior_plan=_prior_plan_context(),
                query="Keep Distributed Systems but replace Algorithms with something lighter.",
            ),
            memory_service=memory_service,
        )
    except ValueError as exc:
        assert "prior plan" in str(exc)
        assert "CS370" in str(exc)
    else:
        raise AssertionError("Expected refinement to reject the out-of-plan title reference.")


def test_refine_semester_plan_rejects_underspecified_request(tmp_path) -> None:
    """Refinement should fail clearly when the request does not contain a supported intent."""
    memory_service = MemoryService(db_path=tmp_path / "refine-vague.db")

    try:
        refine_semester_plan(
            PlanRefineRequest(
                user_id="u_refine_vague",
                prior_plan=_prior_plan_context(),
                query="Change it.",
            ),
            memory_service=memory_service,
        )
    except ValueError as exc:
        assert "too vague" in str(exc)
    else:
        raise AssertionError("Expected refinement to reject the vague request.")


def test_refine_semester_plan_rejects_impossible_constraints(tmp_path) -> None:
    """Refinement should fail clearly when explicit constraints cannot be satisfied together."""
    memory_service = MemoryService(db_path=tmp_path / "refine-impossible.db")

    try:
        refine_semester_plan(
            PlanRefineRequest(
                user_id="u_refine_impossible",
                prior_plan=_prior_plan_context(),
                query="Keep CS340 and avoid morning classes.",
            ),
            memory_service=memory_service,
        )
    except ValueError as exc:
        assert "No validated refinement" in str(exc)
    else:
        raise AssertionError("Expected refinement to reject the impossible request.")
