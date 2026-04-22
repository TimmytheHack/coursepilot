"""Tests for the separate imported sample catalog fixture."""

import json

import pytest

from app.tools.catalog import load_import_sample_catalog, load_import_sample_catalog_by_id
from app.tools.course_search import course_search_in_catalog


def test_load_import_sample_catalog_succeeds() -> None:
    """The separate sample catalog fixture should load and normalize successfully."""
    catalog = load_import_sample_catalog()
    catalog_by_id = load_import_sample_catalog_by_id()

    assert len(catalog) == 7
    assert {"CS115", "CS350", "CS598_AGENTIC_AI", "CS599_ADV_NLP"} <= set(catalog_by_id)
    assert catalog_by_id["CS598_AGENTIC_AI"]["terms_offered"] == ["Fall"]
    assert catalog_by_id["CS599_ADV_NLP"]["prerequisites"] == []


def test_course_search_works_against_imported_sample_catalog() -> None:
    """Deterministic search should operate over the normalized imported sample."""
    catalog = load_import_sample_catalog()

    results = course_search_in_catalog("agentic ai", ["ai"], catalog, max_results=3)

    assert [course["course_id"] for course in results] == ["CS598_AGENTIC_AI", "CS599_ADV_NLP"]


def test_imported_catalog_normalizes_time_slot_terms_to_seasons() -> None:
    """Imported time slots should use the internal season-only term format."""
    catalog_by_id = load_import_sample_catalog_by_id()

    assert catalog_by_id["CS115"]["time_slots"][0]["term"] == "Spring"
    assert catalog_by_id["MA541"]["time_slots"][0]["term"] == "Fall"


def test_imported_catalog_missing_required_field_fails_safely(tmp_path) -> None:
    """Malformed imported catalogs should raise a clear validation error."""
    malformed_catalog_path = tmp_path / "malformed_courses.json"
    malformed_catalog_path.write_text(
        json.dumps(
            [
                {
                    "course_id": "CS_BAD",
                    "title": "Broken Course",
                    "department": "CS",
                    "credits": 4,
                    "description": "Missing required fields on purpose.",
                    "terms_offered": ["Fall 2026"],
                    "prerequisites": [],
                    "corequisites": [],
                    "categories": ["ai"],
                    "difficulty": 3,
                    "workload": 3,
                    "career_tags": ["ai"],
                    "rating_summary": "Broken fixture.",
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required fields: time_slots"):
        load_import_sample_catalog(str(malformed_catalog_path))
