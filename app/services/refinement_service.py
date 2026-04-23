"""Deterministic plan refinement service built on top of the planner."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.models.schemas import CoursePlan, PlanGenerateRequest, PlanRefineRequest, PlanningResponse
from app.services.memory_service import MemoryService
from app.services.planning_service import generate_semester_plan
from app.services.trace_service import TraceService
from app.tools.catalog import DEFAULT_CATALOG_ID, load_catalog, load_catalog_by_id

_COURSE_ID_PATTERN = re.compile(r"\b[A-Z]{2,}\d{2,}(?:_[A-Z0-9]+)?\b")
_TITLE_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_DIRECTION_ALIASES = {
    "ai": {"ai", "machine learning", "ml", "nlp", "vision"},
    "systems": {"systems", "distributed", "operating systems", "infrastructure"},
    "data": {"data", "analytics", "visualization", "database"},
    "security": {"security", "secure"},
    "product": {"product", "application", "applications", "design"},
    "software": {"software", "web", "backend"},
}
_TITLE_REFERENCE_STOPWORDS = {
    "a",
    "an",
    "and",
    "another",
    "but",
    "class",
    "classes",
    "course",
    "courses",
    "drop",
    "easier",
    "hard",
    "harder",
    "keep",
    "less",
    "lighter",
    "more",
    "one",
    "remove",
    "replace",
    "something",
    "the",
    "this",
    "with",
    "without",
}


@dataclass(frozen=True)
class RefinementIntent:
    """Normalized deterministic refinement intent."""

    must_keep_course_ids: tuple[str, ...]
    must_remove_course_ids: tuple[str, ...]
    preferred_directions: tuple[str, ...]
    reduce_workload: bool
    avoid_morning_classes: bool
    reduce_theory: bool


def _normalize(text: str) -> str:
    """Normalize text for stable heuristic matching."""
    return " ".join(text.lower().split())


def _build_trace_id(user_id: str, term: str) -> str:
    """Build the stable trace identifier for one refinement run."""
    return f"refine-{user_id}-{_normalize(term).replace(' ', '-')}"


def _extract_course_ids(text: str) -> list[str]:
    """Extract machine-friendly course IDs from one text string."""
    return list(dict.fromkeys(_COURSE_ID_PATTERN.findall(text.upper())))


def _title_tokens(text: str) -> set[str]:
    """Return significant normalized title-reference tokens."""
    return {
        token
        for token in _TITLE_TOKEN_PATTERN.findall(_normalize(text))
        if token not in _TITLE_REFERENCE_STOPWORDS
    }


def _match_title_references(
    clause: str,
    course_ids: list[str],
    course_catalog_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Match exact or conservatively normalized course-title references."""
    normalized_clause = _normalize(clause)
    exact_matches = [
        course_id
        for course_id in course_ids
        if _normalize(course_catalog_by_id[course_id]["title"]) in normalized_clause
    ]
    if exact_matches:
        return exact_matches

    clause_tokens = _title_tokens(clause)
    partial_matches: list[str] = []
    for course_id in course_ids:
        title_tokens = _title_tokens(course_catalog_by_id[course_id]["title"])
        if not title_tokens:
            continue
        minimum_overlap = min(2, len(title_tokens))
        if len(title_tokens.intersection(clause_tokens)) >= minimum_overlap:
            partial_matches.append(course_id)
    return partial_matches


def _looks_like_unresolved_title_reference(clause: str) -> bool:
    """Return whether a clause appears to reference a course title by text."""
    normalized_clause = _normalize(clause)
    if not any(token in normalized_clause for token in ("keep", "replace", "remove", "drop", "without")):
        return False
    if any(
        placeholder in normalized_clause
        for placeholder in (
            "replace one hard class",
            "replace one difficult class",
            "replace a hard class",
            "replace a difficult class",
            "replace one class",
            "replace a class",
            "with something lighter",
            "with something easier",
        )
    ):
        return False
    return bool(_title_tokens(clause))


def _resolve_clause_course_ids(
    clause: str,
    prior_plan_course_ids: list[str],
    course_catalog_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Resolve one clause to prior-plan course IDs using IDs or title references."""
    explicit_course_ids = [
        course_id
        for course_id in _extract_course_ids(clause)
        if course_id in prior_plan_course_ids
    ]
    if explicit_course_ids:
        return explicit_course_ids

    prior_title_matches = _match_title_references(clause, prior_plan_course_ids, course_catalog_by_id)
    if len(prior_title_matches) == 1:
        return prior_title_matches
    if len(prior_title_matches) > 1:
        ambiguous_list = ", ".join(prior_title_matches)
        raise ValueError(f"Refinement title reference is ambiguous across prior-plan courses: {ambiguous_list}")

    all_catalog_matches = _match_title_references(
        clause,
        list(course_catalog_by_id.keys()),
        course_catalog_by_id,
    )
    non_prior_matches = [
        course_id
        for course_id in all_catalog_matches
        if course_id not in prior_plan_course_ids
    ]
    if non_prior_matches:
        invalid_list = ", ".join(non_prior_matches)
        raise ValueError(f"Refinement can only reference courses from the prior plan: {invalid_list}")

    if _looks_like_unresolved_title_reference(clause):
        raise ValueError(f"No prior-plan course matched title reference: {clause.strip()}")
    return []


def _mentioned_directions(query: str) -> list[str]:
    """Infer a small direction list from a refinement query."""
    normalized_query = _normalize(query)
    return [
        direction
        for direction, aliases in _DIRECTION_ALIASES.items()
        if any(alias in normalized_query for alias in aliases)
    ]


def _course_is_morning(course: dict[str, Any], season: str) -> bool:
    """Return whether a course has a morning meeting in the target season."""
    for slot in course.get("time_slots", []):
        if slot.get("term") != season:
            continue
        if slot["start"] < "12:00":
            return True
    return False


def _course_is_theory_heavy(course: dict[str, Any]) -> bool:
    """Return whether a course looks theory-heavy by local metadata."""
    searchable = " ".join(
        str(value)
        for value in (
            course.get("title", ""),
            *course.get("categories", []),
            *course.get("career_tags", []),
        )
    ).lower()
    return any(token in searchable for token in ("theory", "algorithms", "research"))


def _plan_workload_total(course_ids: list[str], course_catalog_by_id: dict[str, dict[str, Any]]) -> int:
    """Sum deterministic workload scores for a plan."""
    return sum(int(course_catalog_by_id[course_id]["workload"]) for course_id in course_ids)


def _plan_theory_count(course_ids: list[str], course_catalog_by_id: dict[str, dict[str, Any]]) -> int:
    """Count theory-heavy courses in a plan."""
    return sum(1 for course_id in course_ids if _course_is_theory_heavy(course_catalog_by_id[course_id]))


def _plan_keep_overlap(plan: CoursePlan, prior_plan_course_ids: set[str]) -> int:
    """Measure how much of the prior plan remains after refinement."""
    return len(prior_plan_course_ids.intersection(plan.courses))


def _parse_refinement_intent(
    request: PlanRefineRequest,
    course_catalog_by_id: dict[str, dict[str, Any]],
) -> RefinementIntent:
    """Parse the supported deterministic refinement intents from one request."""
    normalized_query = _normalize(request.query)
    prior_plan_course_ids = set(request.prior_plan.courses)
    ordered_prior_plan_course_ids = list(request.prior_plan.courses)
    mentioned_course_ids = [course_id for course_id in _extract_course_ids(request.query) if course_id in course_catalog_by_id]

    must_keep_course_ids: list[str] = []
    must_remove_course_ids: list[str] = []

    for raw_clause in re.split(r"\bbut\b|;", request.query, flags=re.IGNORECASE):
        clause = raw_clause.strip()
        if not clause:
            continue
        clause_course_ids = _resolve_clause_course_ids(
            clause,
            ordered_prior_plan_course_ids,
            course_catalog_by_id,
        )
        normalized_clause = _normalize(clause)
        if "keep" in normalized_clause:
            must_keep_course_ids.extend(course_id for course_id in clause_course_ids if course_id not in must_keep_course_ids)
        if any(token in normalized_clause for token in ("replace", "remove", "drop", "without")):
            must_remove_course_ids.extend(
                course_id for course_id in clause_course_ids if course_id not in must_remove_course_ids
            )

    reduce_workload = any(
        token in normalized_query
        for token in (
            "lighter",
            "less work",
            "lower workload",
            "reduce workload",
            "reduce the workload",
            "easier",
            "hard class",
            "harder class",
        )
    )
    avoid_morning_classes = any(
        token in normalized_query
        for token in ("avoid morning", "no morning", "avoid morning classes", "no morning classes")
    )
    reduce_theory = any(
        token in normalized_query
        for token in ("reduce theory", "less theory", "avoid theory")
    )

    if "replace one hard class" in normalized_query and not must_remove_course_ids:
        sortable_courses = [
            course_id
            for course_id in request.prior_plan.courses
            if course_id not in must_keep_course_ids
        ]
        sortable_courses.sort(
            key=lambda course_id: (
                -int(course_catalog_by_id[course_id]["difficulty"]),
                -int(course_catalog_by_id[course_id]["workload"]),
                course_id,
            )
        )
        if sortable_courses:
            must_remove_course_ids.append(sortable_courses[0])

    if reduce_theory:
        for course_id in request.prior_plan.courses:
            if course_id in must_keep_course_ids:
                continue
            if _course_is_theory_heavy(course_catalog_by_id[course_id]) and course_id not in must_remove_course_ids:
                must_remove_course_ids.append(course_id)

    if must_keep_course_ids and must_remove_course_ids:
        overlap = sorted(set(must_keep_course_ids).intersection(must_remove_course_ids))
        if overlap:
            overlap_list = ", ".join(overlap)
            raise ValueError(f"Refinement cannot both keep and remove the same course(s): {overlap_list}")

    invalid_mentions = sorted(
        course_id
        for course_id in mentioned_course_ids
        if course_id not in prior_plan_course_ids
    )
    if invalid_mentions:
        invalid_list = ", ".join(invalid_mentions)
        raise ValueError(f"Refinement can only reference courses from the prior plan: {invalid_list}")

    mentioned_directions = _mentioned_directions(request.query)
    preferred_directions = list(dict.fromkeys(request.prior_plan.preferred_directions + mentioned_directions))

    if not any((must_keep_course_ids, must_remove_course_ids, reduce_workload, avoid_morning_classes, reduce_theory, mentioned_directions)):
        raise ValueError(
            "Refinement request is too vague. Specify a course to keep or replace, ask for lighter workload, "
            "or request a schedule change such as avoiding morning classes."
        )

    return RefinementIntent(
        must_keep_course_ids=tuple(must_keep_course_ids),
        must_remove_course_ids=tuple(must_remove_course_ids),
        preferred_directions=tuple(preferred_directions),
        reduce_workload=reduce_workload,
        avoid_morning_classes=avoid_morning_classes,
        reduce_theory=reduce_theory,
    )


def _select_refined_plan(
    plans: list[CoursePlan],
    request: PlanRefineRequest,
    intent: RefinementIntent,
    course_catalog_by_id: dict[str, dict[str, Any]],
) -> CoursePlan:
    """Choose the best validated refined plan from planner output."""
    prior_plan_course_ids = set(request.prior_plan.courses)
    prior_workload_total = _plan_workload_total(request.prior_plan.courses, course_catalog_by_id)
    prior_theory_count = _plan_theory_count(request.prior_plan.courses, course_catalog_by_id)
    must_keep_set = set(intent.must_keep_course_ids)
    must_remove_set = set(intent.must_remove_course_ids)
    season = request.prior_plan.term.split(" ", 1)[0]

    compatible_plans: list[CoursePlan] = []
    for plan in plans:
        plan_course_ids = set(plan.courses)
        if must_keep_set and not must_keep_set.issubset(plan_course_ids):
            continue
        if must_remove_set.intersection(plan_course_ids):
            continue
        if intent.reduce_workload and _plan_workload_total(plan.courses, course_catalog_by_id) >= prior_workload_total:
            continue
        if intent.reduce_theory and _plan_theory_count(plan.courses, course_catalog_by_id) >= prior_theory_count:
            continue
        if intent.avoid_morning_classes and any(
            _course_is_morning(course_catalog_by_id[course_id], season)
            for course_id in plan.courses
        ):
            continue
        compatible_plans.append(plan)

    if not compatible_plans:
        raise ValueError(
            "No validated refinement satisfied the requested keep/remove and workload constraints."
        )

    return max(
        compatible_plans,
        key=lambda plan: (
            _plan_keep_overlap(plan, prior_plan_course_ids),
            len(must_keep_set.intersection(plan.courses)),
            prior_workload_total - _plan_workload_total(plan.courses, course_catalog_by_id),
            plan.fit_score,
        ),
    )


def refine_semester_plan(
    request: PlanRefineRequest,
    memory_service: MemoryService | None = None,
    trace_service: TraceService | None = None,
    course_catalog: list[dict[str, Any]] | None = None,
    course_catalog_by_id: dict[str, dict[str, Any]] | None = None,
    degree_requirements: dict[str, Any] | None = None,
    catalog_id: str = DEFAULT_CATALOG_ID,
) -> PlanningResponse:
    """Refine one prior plan with deterministic heuristics and validation."""
    resolved_memory_service = memory_service or MemoryService()
    resolved_trace_service = trace_service or TraceService()
    resolved_course_catalog = course_catalog or load_catalog(catalog_id)
    resolved_course_catalog_by_id = course_catalog_by_id or load_catalog_by_id(catalog_id)
    trace_id = _build_trace_id(request.user_id, request.prior_plan.term)

    unknown_prior_courses = [
        course_id
        for course_id in request.prior_plan.courses
        if course_id not in resolved_course_catalog_by_id
    ]
    if unknown_prior_courses:
        unknown_list = ", ".join(sorted(set(unknown_prior_courses)))
        raise ValueError(f"Prior plan contains unknown course IDs: {unknown_list}")

    resolved_trace_service.start_trace(trace_id, user_id=request.user_id, term=request.prior_plan.term)
    intent = _parse_refinement_intent(request, resolved_course_catalog_by_id)
    resolved_trace_service.record_stage(
        trace_id,
        "parse_refinement_intent",
        {
            "must_keep_course_ids": list(intent.must_keep_course_ids),
            "must_remove_course_ids": list(intent.must_remove_course_ids),
            "preferred_directions": list(intent.preferred_directions),
            "reduce_workload": intent.reduce_workload,
            "avoid_morning_classes": intent.avoid_morning_classes,
            "reduce_theory": intent.reduce_theory,
        },
    )

    prior_total_credits = sum(int(resolved_course_catalog_by_id[course_id]["credits"]) for course_id in request.prior_plan.courses)
    target_max_credits = request.prior_plan.max_credits
    if intent.reduce_workload and prior_total_credits > 4:
        target_max_credits = min(request.prior_plan.max_credits, max(4, prior_total_credits - 4))

    planning_request = PlanGenerateRequest(
        user_id=request.user_id,
        query=f"{request.prior_plan.query} {request.query}".strip(),
        term=request.prior_plan.term,
        completed_courses=request.prior_plan.completed_courses,
        preferred_directions=list(intent.preferred_directions),
        max_courses=request.prior_plan.max_courses,
        max_credits=target_max_credits,
        avoid_morning_classes=request.prior_plan.avoid_morning_classes or intent.avoid_morning_classes,
    )
    resolved_trace_service.record_stage(
        trace_id,
        "derive_refinement_constraints",
        {
            "max_courses": planning_request.max_courses,
            "max_credits": planning_request.max_credits,
            "avoid_morning_classes": planning_request.avoid_morning_classes,
            "excluded_course_ids": list(intent.must_remove_course_ids),
            "required_course_ids": list(intent.must_keep_course_ids),
        },
    )

    try:
        planner_response = generate_semester_plan(
            planning_request,
            memory_service=resolved_memory_service,
            course_catalog=resolved_course_catalog,
            course_catalog_by_id=resolved_course_catalog_by_id,
            degree_requirements=degree_requirements,
            required_course_ids=list(intent.must_keep_course_ids),
            excluded_course_ids=list(intent.must_remove_course_ids),
        )
    except ValueError as exc:
        resolved_trace_service.record_stage(
            trace_id,
            "rerun_planner_with_constraints",
            {"status": "failed", "detail": str(exc)},
        )
        raise ValueError(
            "No validated refinement could be generated for the requested changes."
        ) from exc

    resolved_trace_service.record_stage(
        trace_id,
        "rerun_planner_with_constraints",
        {
            "status": "completed",
            "planner_trace_id": planner_response.trace_id,
            "candidate_labels": [plan.label for plan in planner_response.plans],
        },
    )

    refined_base_plan = _select_refined_plan(
        planner_response.plans,
        request,
        intent,
        resolved_course_catalog_by_id,
    )
    refined_plan = CoursePlan(
        label="refined",
        courses=refined_base_plan.courses,
        total_credits=refined_base_plan.total_credits,
        rationale=(
            f"Refined from {request.prior_plan.plan_id}. {refined_base_plan.rationale}"
        ),
        validation_facts=refined_base_plan.validation_facts,
        risks=refined_base_plan.risks,
        fit_score=refined_base_plan.fit_score,
    )
    resolved_trace_service.record_stage(
        trace_id,
        "select_refined_plan",
        {
            "selected_courses": refined_plan.courses,
            "selected_total_credits": refined_plan.total_credits,
        },
    )

    explicit_rejections = [
        course_id
        for course_id in intent.must_remove_course_ids
        if course_id in _extract_course_ids(request.query)
    ]
    for course_id in explicit_rejections:
        resolved_memory_service.record_rejected_course(request.user_id, course_id, request.query)
    resolved_trace_service.record_stage(
        trace_id,
        "persist_refinement_feedback",
        {
            "rejected_course_ids": explicit_rejections,
        },
    )

    return PlanningResponse(
        trace_id=trace_id,
        plans=[refined_plan],
        summary=(
            f"Refined {request.prior_plan.plan_id} into 1 validated plan for {request.prior_plan.term} "
            "using deterministic planning constraints."
        ),
        next_actions=[
            "Review whether the revised plan preserves the intended academic focus.",
            "If needed, refine again with a specific course replacement or tighter schedule preference.",
        ],
    )
