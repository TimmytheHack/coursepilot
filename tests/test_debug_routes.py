"""Route-level tests for read-only debug visibility endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.memory_service import MemoryService
from app.services.trace_service import TraceService


client = TestClient(app)


def test_debug_traces_returns_matching_trace_for_user_and_term() -> None:
    """Trace debug route should return matching traces with stable structure."""
    trace_service = TraceService()
    trace_service.start_trace("trace-debug-2", user_id="u_debug_trace", term="Spring 2026")
    trace_service.record_stage("trace-debug-2", "build_response", {"plan_labels": ["balanced"]})
    trace_service.start_trace("trace-debug-1", user_id="u_debug_trace", term="Fall 2026")
    trace_service.record_stage("trace-debug-1", "retrieve_courses", {"retrieved_count": 3})
    trace_service.start_trace("trace-debug-other", user_id="u_other_trace", term="Fall 2026")
    trace_service.record_stage("trace-debug-other", "retrieve_courses", {"retrieved_count": 1})

    response = client.get("/debug/traces", params={"user_id": "u_debug_trace", "term": "Fall 2026"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "u_debug_trace",
        "term": "Fall 2026",
        "trace_id": None,
        "traces": [
            {
                "trace_id": "trace-debug-1",
                "user_id": "u_debug_trace",
                "term": "Fall 2026",
                "stage_count": 1,
                "stages": [{"stage": "retrieve_courses", "details": {"retrieved_count": 3}}],
            }
        ],
    }


def test_debug_traces_returns_empty_results_when_no_match() -> None:
    """Trace debug route should return stable empty results when nothing matches."""
    response = client.get("/debug/traces", params={"user_id": "u_trace_missing"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "u_trace_missing",
        "term": None,
        "trace_id": None,
        "traces": [],
    }


def test_debug_memory_returns_profile_and_entries(monkeypatch, tmp_path) -> None:
    """Memory debug route should return a typed snapshot of stored user memory."""
    db_path = tmp_path / "debug-memory.db"
    memory_service = MemoryService(db_path=db_path)
    memory_service.save_user_profile("u_debug_memory", {"completed_courses": ["CS101"], "year": "Junior"})
    memory_service.upsert_memory("u_debug_memory", "preference", "preferred_directions", ["ai", "product"])
    memory_service.record_rejected_course("u_debug_memory", "CS310", "Too theoretical.")
    monkeypatch.setenv("COURSEPILOT_DB_PATH", str(db_path))

    response = client.get("/debug/memory", params={"user_id": "u_debug_memory"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "u_debug_memory",
        "memory_type": None,
        "profile": {"completed_courses": ["CS101"], "year": "Junior"},
        "entries": [
            {
                "memory_type": "preference",
                "key": "preferred_directions",
                "value": ["ai", "product"],
            },
            {
                "memory_type": "rejected_course",
                "key": "CS310",
                "value": "Too theoretical.",
            },
        ],
    }


def test_debug_memory_supports_type_filter_and_is_read_only(monkeypatch, tmp_path) -> None:
    """Memory debug route should filter by type without mutating stored data."""
    db_path = tmp_path / "debug-memory-filter.db"
    memory_service = MemoryService(db_path=db_path)
    memory_service.save_user_profile("u_debug_readonly", {"completed_courses": ["CS120"]})
    memory_service.upsert_memory("u_debug_readonly", "preference", "preferred_directions", ["systems"])
    memory_service.record_rejected_course("u_debug_readonly", "CS340", "Morning section.")
    before_entries = memory_service.get_memories("u_debug_readonly")
    monkeypatch.setenv("COURSEPILOT_DB_PATH", str(db_path))

    response = client.get(
        "/debug/memory",
        params={"user_id": "u_debug_readonly", "memory_type": "rejected_course"},
    )
    after_entries = memory_service.get_memories("u_debug_readonly")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "u_debug_readonly",
        "memory_type": "rejected_course",
        "profile": {"completed_courses": ["CS120"]},
        "entries": [
            {
                "memory_type": "rejected_course",
                "key": "CS340",
                "value": "Morning section.",
            }
        ],
    }
    assert after_entries == before_entries


def test_debug_memory_returns_empty_results_for_unknown_user(monkeypatch, tmp_path) -> None:
    """Memory debug route should return a stable empty snapshot for unknown users."""
    monkeypatch.setenv("COURSEPILOT_DB_PATH", str(tmp_path / "debug-empty.db"))

    response = client.get("/debug/memory", params={"user_id": "u_memory_missing"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "u_memory_missing",
        "memory_type": None,
        "profile": {},
        "entries": [],
    }


def test_debug_routes_require_user_id() -> None:
    """Debug routes should reject requests that omit the required user identifier."""
    traces_response = client.get("/debug/traces")
    memory_response = client.get("/debug/memory")

    assert traces_response.status_code == 422
    assert memory_response.status_code == 422
