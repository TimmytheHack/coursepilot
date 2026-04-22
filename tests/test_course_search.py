"""Unit tests for the deterministic course search tool."""

from app.tools.course_search import course_search


def test_course_search_returns_ranked_matches_for_query() -> None:
    """Machine learning queries should rank relevant AI courses first."""
    results = course_search("machine learning", ["ai"], max_results=3)

    assert [course["course_id"] for course in results] == ["CS340", "CS330", "CS240"]


def test_course_search_returns_no_results_for_unmatched_query() -> None:
    """Search should return an empty list when no course matches."""
    results = course_search("ancient pottery", [], max_results=5)

    assert results == []


def test_course_search_uses_preferred_directions_to_break_ties() -> None:
    """Preference tags should influence ordering for ambiguous searches."""
    results = course_search("engineering", ["security"], max_results=2)

    assert [course["course_id"] for course in results] == ["CS410", "CS220"]


def test_course_search_limits_result_count() -> None:
    """Search should honor the requested maximum number of results."""
    results = course_search("", ["ai"], max_results=2)

    assert len(results) == 2


def test_course_search_handles_empty_query_with_preferences() -> None:
    """An empty query should still return preference-aligned results."""
    results = course_search("", ["systems"], max_results=3)

    assert [course["course_id"] for course in results] == ["CS210", "CS230", "CS320"]
