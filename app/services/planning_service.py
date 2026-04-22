"""Deterministic planning service for CoursePilot semester plans."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from app.models.schemas import CoursePlan, PlanGenerateRequest, PlanningResponse
from app.services.memory_service import MemoryService
from app.tools.catalog import load_course_catalog, load_course_catalog_by_id
from app.tools.course_search import course_search
from app.tools.graduation_checker import graduation_checker
from app.tools.prerequisite_checker import prerequisite_checker
from app.tools.schedule_conflict_checker import schedule_conflict_checker
from app.tools.workload_estimator import workload_estimator

DEGREE_REQUIREMENTS_PATH = Path(__file__).resolve().parents[2] / "data" / "degree_requirements.json"


@lru_cache(maxsize=1)
def _load_degree_requirements() -> dict[str, Any]:
    """Load the local sample degree requirements."""
    with DEGREE_REQUIREMENTS_PATH.open("r", encoding="utf-8") as requirements_file:
        requirements = json.load(requirements_file)

    if not isinstance(requirements, dict):
        raise ValueError("Degree requirements must be a JSON object.")
    return requirements


def _term_season(term: str) -> str:
    """Extract the catalog season token from a user-facing term string."""
    return term.strip().split(" ", 1)[0]


def _normalize(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    return " ".join(text.lower().split())


def _infer_preferred_directions(query: str) -> list[str]:
    """Infer a small direction list from the request query."""
    direction_aliases = {
        "ai": {"ai", "machine learning", "ml", "nlp", "vision"},
        "systems": {"systems", "distributed", "operating systems", "infrastructure"},
        "data": {"data", "analytics", "visualization", "database"},
        "security": {"security", "secure"},
        "product": {"product", "application", "applications", "design"},
        "software": {"software", "web", "backend"},
    }
    normalized_query = _normalize(query)
    inferred = [
        direction
        for direction, aliases in direction_aliases.items()
        if any(alias in normalized_query for alias in aliases)
    ]
    return inferred


def _course_is_morning(course: dict[str, Any], season: str) -> bool:
    """Return whether a course has a morning meeting in the target season."""
    for slot in course.get("time_slots", []):
        if slot.get("term") != season:
            continue
        if slot["start"] < "12:00":
            return True
    return False


def _course_matches_preferences(course: dict[str, Any], preferred_directions: list[str]) -> bool:
    """Return whether a course aligns with explicit or inferred preferences."""
    if not preferred_directions:
        return False

    searchable = _normalize(" ".join(course["categories"] + course["career_tags"]))
    return any(_normalize(direction) in searchable for direction in preferred_directions)


def _candidate_rankings(
    request: PlanGenerateRequest,
    season: str,
    course_catalog: list[dict[str, Any]],
    course_catalog_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retrieve and filter ranked course candidates for the request."""
    preferred_directions = request.preferred_directions or _infer_preferred_directions(request.query)
    ranked_courses = course_search(request.query, preferred_directions, max_results=12)
    if not ranked_courses:
        ranked_courses = course_search("", preferred_directions, max_results=12)

    ranked_ids = [course["course_id"] for course in ranked_courses]
    for course in course_catalog:
        if course["course_id"] not in ranked_ids:
            ranked_courses.append(course)

    prerequisite_results = {
        result["course_id"]: result
        for result in prerequisite_checker(
            request.completed_courses,
            [course["course_id"] for course in ranked_courses],
            course_catalog_by_id,
        )
    }

    eligible_courses: list[dict[str, Any]] = []
    for index, course in enumerate(ranked_courses):
        course_id = course["course_id"]
        if course_id in request.completed_courses:
            continue
        if season not in course.get("terms_offered", []):
            continue
        if request.avoid_morning_classes and _course_is_morning(course, season):
            continue
        if not prerequisite_results[course_id]["satisfied"]:
            continue

        eligible_courses.append(
            {
                "course": course,
                "rank_index": index,
                "preference_match": _course_matches_preferences(course, preferred_directions),
            }
        )

    return eligible_courses


def _variant_sort_key(variant: str, ranked_course: dict[str, Any]) -> tuple[Any, ...]:
    """Return a variant-specific ordering key for candidate selection."""
    course = ranked_course["course"]
    preference_bonus = 0 if ranked_course["preference_match"] else 1
    rank_index = ranked_course["rank_index"]

    if variant == "ambitious":
        return (-int(course["difficulty"]), -int(course["workload"]), preference_bonus, rank_index, course["course_id"])
    if variant == "conservative":
        return (int(course["workload"]), int(course["difficulty"]), preference_bonus, rank_index, course["course_id"])
    return (
        abs(int(course["workload"]) - 3) + abs(int(course["difficulty"]) - 3),
        preference_bonus,
        rank_index,
        course["course_id"],
    )


def _target_course_count(variant: str, max_courses: int) -> int:
    """Choose a variant-specific target plan size."""
    if variant == "conservative":
        return max(2, min(max_courses - 1, 3)) if max_courses > 1 else 1
    return min(max_courses, 3)


def _select_courses_for_variant(
    variant: str,
    candidates: list[dict[str, Any]],
    request: PlanGenerateRequest,
    season: str,
    course_catalog_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Build a deterministic course set for one planning variant."""
    selected_courses: list[str] = []
    total_credits = 0
    target_count = _target_course_count(variant, request.max_courses)

    for ranked_course in sorted(candidates, key=lambda item: _variant_sort_key(variant, item)):
        course = ranked_course["course"]
        course_id = course["course_id"]
        course_credits = int(course["credits"])
        if total_credits + course_credits > request.max_credits:
            continue

        tentative_courses = selected_courses + [course_id]
        if schedule_conflict_checker(tentative_courses, season, course_catalog_by_id):
            continue

        selected_courses.append(course_id)
        total_credits += course_credits
        if len(selected_courses) >= target_count:
            break

    return selected_courses


def _fit_score(
    variant: str,
    selected_courses: list[str],
    candidates: list[dict[str, Any]],
    workload_summary: dict[str, Any],
) -> float:
    """Estimate a bounded fit score from deterministic planner signals."""
    if not selected_courses:
        return 0.0

    selected_lookup = {course_id for course_id in selected_courses}
    candidate_count = max(len(candidates), 1)
    rank_positions = [
        ranked_course["rank_index"]
        for ranked_course in candidates
        if ranked_course["course"]["course_id"] in selected_lookup
    ]
    rank_component = sum(1 - (position / candidate_count) for position in rank_positions) / len(rank_positions)

    preference_hits = sum(
        1 for ranked_course in candidates
        if ranked_course["course"]["course_id"] in selected_lookup and ranked_course["preference_match"]
    )
    preference_component = preference_hits / len(selected_courses)

    if variant == "ambitious":
        workload_component = min(float(workload_summary["average_difficulty"]) / 4.0, 1.0)
    elif variant == "conservative":
        workload_component = max(0.0, 1 - (float(workload_summary["average_workload"]) - 2.0) / 3.0)
    else:
        workload_component = max(0.0, 1 - abs(float(workload_summary["average_workload"]) - 3.0) / 3.0)

    score = (0.45 * rank_component) + (0.25 * preference_component) + (0.30 * workload_component)
    return round(min(max(score, 0.0), 1.0), 2)


def _build_rationale(variant: str) -> str:
    """Return a stable rationale string for the plan variant."""
    if variant == "ambitious":
        return "Prioritizes higher-challenge courses that still pass prerequisite and conflict checks."
    if variant == "conservative":
        return "Prefers a lighter course load while preserving progress with valid offerings."
    return "Balances course relevance with moderate workload and difficulty."


def _build_risks(
    selected_courses: list[str],
    target_count: int,
    workload_summary: dict[str, Any],
    graduation_summary: dict[str, Any],
) -> list[str]:
    """Build user-visible risk notes from validation results."""
    risks: list[str] = []
    if len(selected_courses) < target_count:
        risks.append("Current constraints leave fewer valid courses than the target plan size.")
    if workload_summary["workload_label"] == "heavy":
        risks.append("Aggregate workload is heavy for a single semester.")

    remaining_requirements = [
        requirement["name"]
        for requirement in graduation_summary["requirements"]
        if not requirement["satisfied_after"]
    ]
    if remaining_requirements:
        risks.append(
            "Degree progress remains incomplete after this plan: "
            + ", ".join(remaining_requirements)
            + "."
        )

    if not risks:
        risks.append("No severe validation issues were detected for this draft plan.")
    return risks


def _request_to_data(request: PlanGenerateRequest) -> dict[str, Any]:
    """Convert a request model to a plain dictionary across Pydantic versions."""
    if hasattr(request, "model_dump"):
        return request.model_dump()
    return request.dict()


def _request_with_memory_context(
    request: PlanGenerateRequest,
    memory_service: MemoryService,
) -> PlanGenerateRequest:
    """Merge stored memory context into a planning request when fields are omitted."""
    user_context = memory_service.load_user_context(request.user_id)
    request_data = _request_to_data(request)

    completed_courses = request.completed_courses or user_context["completed_courses"]
    preferred_directions = request.preferred_directions or user_context["preferred_directions"]

    if request.completed_courses:
        memory_service.save_user_profile(
            request.user_id,
            {"completed_courses": request.completed_courses},
        )
    if request.preferred_directions:
        memory_service.upsert_memory(
            request.user_id,
            "preference",
            "preferred_directions",
            request.preferred_directions,
        )

    return PlanGenerateRequest(
        **{
            **request_data,
            "completed_courses": completed_courses,
            "preferred_directions": preferred_directions,
        }
    )


def generate_semester_plan(
    request: PlanGenerateRequest,
    memory_service: MemoryService | None = None,
) -> PlanningResponse:
    """Generate deterministic candidate semester plans from local tools and data."""
    resolved_memory_service = memory_service or MemoryService()
    resolved_request = _request_with_memory_context(request, resolved_memory_service)
    season = _term_season(resolved_request.term)
    course_catalog = load_course_catalog()
    course_catalog_by_id = load_course_catalog_by_id()
    degree_requirements = _load_degree_requirements()
    candidates = _candidate_rankings(resolved_request, season, course_catalog, course_catalog_by_id)

    variants = ("balanced", "ambitious", "conservative")
    built_plans: list[CoursePlan] = []
    seen_course_sets: set[tuple[str, ...]] = set()
    for variant in variants:
        selected_courses = _select_courses_for_variant(
            variant,
            candidates,
            resolved_request,
            season,
            course_catalog_by_id,
        )
        if not selected_courses:
            continue

        course_key = tuple(selected_courses)
        if course_key in seen_course_sets:
            continue

        prerequisite_results = prerequisite_checker(
            resolved_request.completed_courses,
            selected_courses,
            course_catalog_by_id,
        )
        if not all(result["satisfied"] for result in prerequisite_results):
            continue

        if schedule_conflict_checker(selected_courses, season, course_catalog_by_id):
            continue

        workload_summary = workload_estimator(selected_courses, course_catalog_by_id)
        graduation_summary = graduation_checker(
            resolved_request.completed_courses,
            selected_courses,
            degree_requirements,
        )
        target_count = _target_course_count(variant, resolved_request.max_courses)

        built_plans.append(
            CoursePlan(
                label=variant,
                courses=selected_courses,
                total_credits=int(workload_summary["total_credits"]),
                rationale=_build_rationale(variant),
                risks=_build_risks(
                    selected_courses,
                    target_count,
                    workload_summary,
                    graduation_summary,
                ),
                fit_score=_fit_score(variant, selected_courses, candidates, workload_summary),
            )
        )
        seen_course_sets.add(course_key)

    if not built_plans:
        raise ValueError("No valid plans could be generated from the current request constraints.")

    summary = (
        f"Generated {len(built_plans)} validated plan option(s) for {resolved_request.term} "
        f"using deterministic search and validation tools."
    )
    next_actions = [
        "Review which plan variant best matches the intended workload.",
        "Add persistent user memory next so completed courses and preferences do not need to be resent.",
    ]
    return PlanningResponse(
        trace_id=f"plan-{resolved_request.user_id}-{_normalize(resolved_request.term).replace(' ', '-')}",
        plans=built_plans,
        summary=summary,
        next_actions=next_actions,
    )
