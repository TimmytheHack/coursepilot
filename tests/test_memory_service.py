"""Tests for SQLite-backed memory persistence."""

from app.services.memory_service import MemoryService


def test_memory_service_reads_and_writes_user_context(tmp_path) -> None:
    """Memory service should persist profiles, preferences, and rejected courses."""
    memory_service = MemoryService(db_path=tmp_path / "memory.db")

    memory_service.save_user_profile(
        "u_memory",
        {"completed_courses": ["CS101", "CS120"], "year": "Sophomore"},
    )
    memory_service.upsert_memory(
        "u_memory",
        "preference",
        "preferred_directions",
        ["ai", "product"],
    )
    memory_service.record_rejected_course("u_memory", "CS310", "Too theoretical right now.")

    context = memory_service.load_user_context("u_memory")

    assert context["completed_courses"] == ["CS101", "CS120"]
    assert context["preferred_directions"] == ["ai", "product"]
    assert context["rejected_courses"] == {"CS310": "Too theoretical right now."}
    assert context["profile"]["year"] == "Sophomore"
