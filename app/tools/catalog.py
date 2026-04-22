"""Shared helpers for reading the local sample course catalog."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "courses.json"


@lru_cache(maxsize=1)
def load_course_catalog() -> list[dict[str, Any]]:
    """Load the local sample course catalog from JSON."""
    with CATALOG_PATH.open("r", encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    if not isinstance(catalog, list):
        raise ValueError("Course catalog must be a list of course objects.")
    return catalog


@lru_cache(maxsize=1)
def load_course_catalog_by_id() -> dict[str, dict[str, Any]]:
    """Index the local course catalog by course identifier."""
    catalog = load_course_catalog()
    return {course["course_id"]: course for course in catalog}
