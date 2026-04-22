"""Deterministic course search over the local sample catalog."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "courses.json"


@lru_cache(maxsize=1)
def _load_course_catalog() -> list[dict[str, Any]]:
    """Load the local sample course catalog."""
    with CATALOG_PATH.open("r", encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    if not isinstance(catalog, list):
        raise ValueError("Course catalog must be a list of course objects.")
    return catalog


def _normalize(text: str) -> str:
    """Normalize text for deterministic case-insensitive matching."""
    return " ".join(text.lower().split())


def _tokenize(text: str) -> list[str]:
    """Split normalized text into useful search terms."""
    return [token for token in _normalize(text).split(" ") if len(token) >= 2]


def _score_course(
    course: dict[str, Any],
    query_terms: list[str],
    preferred_directions: list[str],
) -> int:
    """Score a course using explicit text and preference signals."""
    searchable_sections = [
        _normalize(str(course["course_id"])),
        _normalize(str(course["title"])),
        _normalize(str(course["description"])),
        _normalize(" ".join(course["categories"])),
        _normalize(" ".join(course["career_tags"])),
    ]
    id_and_title = searchable_sections[:2]
    categories_and_tags = searchable_sections[3:]
    score = 0

    # Favor precise matches first, then descriptive matches, then preference nudges.
    for term in query_terms:
        if any(term == field for field in id_and_title):
            score += 40
        if any(term in field for field in id_and_title):
            score += 20
        if term in searchable_sections[2]:
            score += 8
        if any(term in field for field in categories_and_tags):
            score += 12

    for direction in preferred_directions:
        direction_term = _normalize(direction)
        if any(direction_term in field for field in categories_and_tags):
            score += 10

    return score


def course_search(
    query: str,
    preferred_directions: list[str],
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search the local sample catalog with deterministic ranking heuristics."""
    if max_results <= 0:
        raise ValueError("max_results must be greater than zero.")

    catalog = _load_course_catalog()
    query_terms = _tokenize(query)
    normalized_preferences = [_normalize(direction) for direction in preferred_directions]

    scored_courses: list[tuple[int, dict[str, Any]]] = []
    for course in catalog:
        score = _score_course(course, query_terms, normalized_preferences)
        if score > 0 or (not query_terms and normalized_preferences):
            scored_courses.append((score, course))

    if not query_terms and not normalized_preferences:
        return catalog[:max_results]

    ranked_courses = sorted(
        scored_courses,
        key=lambda item: (-item[0], item[1]["course_id"]),
    )
    return [course for _, course in ranked_courses[:max_results]]
