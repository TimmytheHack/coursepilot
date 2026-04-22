"""Tests for structured planner trace capture."""

from app.services.trace_service import TraceService


def test_trace_service_stores_stage_history() -> None:
    """Trace service should retain structured stage snapshots."""
    trace_service = TraceService()
    trace_service.start_trace("trace-1", user_id="u_trace", term="Fall 2026")
    trace_service.record_stage("trace-1", "retrieve_courses", {"retrieved_count": 4})

    trace = trace_service.get_trace("trace-1")

    assert trace is not None
    assert trace["trace_id"] == "trace-1"
    assert trace["stages"] == [{"stage": "retrieve_courses", "details": {"retrieved_count": 4}}]
