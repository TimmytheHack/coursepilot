"""Shared helpers for reading the local sample course catalog."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "courses.json"
SAMPLE_IMPORT_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "imports" / "bu_sample_courses.json"
REQUIRED_COURSE_FIELDS = {
    "course_id",
    "title",
    "department",
    "credits",
    "description",
    "terms_offered",
    "prerequisites",
    "corequisites",
    "categories",
    "difficulty",
    "workload",
    "time_slots",
    "career_tags",
    "rating_summary",
}
_COURSE_ID_PATTERN = re.compile(r"\b[A-Z]{2,}\d{2,}(?:_[A-Z0-9]+)?\b")
_ALLOWED_TERM_PREFIXES = {"Fall", "Spring", "Summer", "Winter"}


def _read_catalog(path: Path) -> list[dict[str, Any]]:
    """Read a raw catalog JSON file."""
    with path.open("r", encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    if not isinstance(catalog, list):
        raise ValueError("Course catalog must be a list of course objects.")
    return catalog


def _normalize_term_value(term: str) -> str:
    """Normalize full term strings to the season tokens used internally."""
    normalized_term = term.strip()
    if not normalized_term:
        raise ValueError("Term values must not be empty.")

    first_token = normalized_term.split(" ", 1)[0]
    if first_token not in _ALLOWED_TERM_PREFIXES:
        raise ValueError(f"Unsupported term value: {term}")
    return first_token


def _normalize_requisites(values: list[Any]) -> list[str]:
    """Extract deterministic course-id-like prerequisite tokens."""
    normalized_values: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Prerequisites and corequisites must be strings.")
        for token in _COURSE_ID_PATTERN.findall(value.upper()):
            if token not in normalized_values:
                normalized_values.append(token)
    return normalized_values


def _normalize_time_slots(time_slots: list[Any], course_id: str) -> list[dict[str, Any]]:
    """Normalize imported time slots to the internal season-based term shape."""
    normalized_slots: list[dict[str, Any]] = []
    for slot in time_slots:
        if not isinstance(slot, dict):
            raise ValueError(f"Course {course_id} has a non-object time slot.")
        if "term" not in slot:
            raise ValueError(f"Course {course_id} has a time slot without a term.")

        normalized_slot = dict(slot)
        normalized_slot["term"] = _normalize_term_value(str(slot["term"]))
        normalized_slots.append(normalized_slot)
    return normalized_slots


def _normalize_imported_course(course: dict[str, Any]) -> dict[str, Any]:
    """Normalize one imported course object to the repo's internal schema."""
    missing_fields = sorted(REQUIRED_COURSE_FIELDS - set(course.keys()))
    course_id = str(course.get("course_id", "<unknown>"))
    if missing_fields:
        missing_list = ", ".join(missing_fields)
        raise ValueError(f"Course {course_id} is missing required fields: {missing_list}")

    return {
        "course_id": str(course["course_id"]),
        "title": str(course["title"]),
        "department": str(course["department"]),
        "credits": int(course["credits"]),
        "description": str(course["description"]),
        "terms_offered": [
            _normalize_term_value(str(term))
            for term in course["terms_offered"]
        ],
        "prerequisites": _normalize_requisites(list(course["prerequisites"])),
        "corequisites": _normalize_requisites(list(course["corequisites"])),
        "categories": [str(category) for category in course["categories"]],
        "difficulty": int(course["difficulty"]),
        "workload": int(course["workload"]),
        "time_slots": _normalize_time_slots(list(course["time_slots"]), course_id),
        "career_tags": [str(tag) for tag in course["career_tags"]],
        "rating_summary": str(course["rating_summary"]),
    }


@lru_cache(maxsize=1)
def load_course_catalog() -> list[dict[str, Any]]:
    """Load the local sample course catalog from JSON."""
    return _read_catalog(CATALOG_PATH)


@lru_cache(maxsize=1)
def load_course_catalog_by_id() -> dict[str, dict[str, Any]]:
    """Index the local course catalog by course identifier."""
    catalog = load_course_catalog()
    return {course["course_id"]: course for course in catalog}


@lru_cache(maxsize=4)
def load_import_sample_catalog(path: str | None = None) -> list[dict[str, Any]]:
    """Load and normalize the separate BU sample catalog fixture."""
    catalog_path = Path(path) if path is not None else SAMPLE_IMPORT_CATALOG_PATH
    raw_catalog = _read_catalog(catalog_path)
    return [_normalize_imported_course(course) for course in raw_catalog]


@lru_cache(maxsize=4)
def load_import_sample_catalog_by_id(path: str | None = None) -> dict[str, dict[str, Any]]:
    """Index the normalized sample import catalog by course identifier."""
    catalog = load_import_sample_catalog(path)
    return {course["course_id"]: course for course in catalog}
