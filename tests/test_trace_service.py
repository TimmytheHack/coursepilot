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


def test_trace_service_lists_matching_traces_with_stable_filters() -> None:
    """Trace service should filter traces by user, term, and trace ID."""
    trace_service = TraceService()
    trace_service.start_trace("trace-list-1", user_id="u_trace_list", term="Fall 2026")
    trace_service.record_stage("trace-list-1", "build_response", {"plan_labels": ["balanced"]})
    trace_service.start_trace("trace-list-2", user_id="u_trace_list", term="Spring 2026")
    trace_service.start_trace("trace-list-3", user_id="u_trace_other", term="Fall 2026")

    traces = trace_service.list_traces(user_id="u_trace_list", term="Fall 2026")
    exact_trace = trace_service.list_traces(user_id="u_trace_list", trace_id="trace-list-2")

    assert [trace["trace_id"] for trace in traces] == ["trace-list-1"]
    assert [trace["trace_id"] for trace in exact_trace] == ["trace-list-2"]
