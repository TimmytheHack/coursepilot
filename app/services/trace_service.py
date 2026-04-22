"""Structured in-memory trace capture for planner debugging."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class TraceService:
    """Store safe structured planner traces keyed by trace identifier."""

    _traces: dict[str, dict[str, Any]] = {}

    def start_trace(self, trace_id: str, *, user_id: str, term: str) -> None:
        """Initialize a trace record."""
        self._traces[trace_id] = {
            "trace_id": trace_id,
            "user_id": user_id,
            "term": term,
            "stages": [],
        }

    def record_stage(self, trace_id: str, stage: str, details: dict[str, Any]) -> None:
        """Append one stage snapshot to an existing trace."""
        trace = self._traces.setdefault(trace_id, {"trace_id": trace_id, "stages": []})
        trace.setdefault("stages", []).append({"stage": stage, "details": deepcopy(details)})

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Return a copy of the stored trace for debugging."""
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        return deepcopy(trace)

    def list_traces(
        self,
        *,
        user_id: str,
        term: str | None = None,
        trace_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return matching traces with stable ordering for debug views."""
        matching_traces = [
            deepcopy(stored_trace)
            for stored_trace in self._traces.values()
            if stored_trace.get("user_id") == user_id
            and (term is None or stored_trace.get("term") == term)
            and (trace_id is None or stored_trace.get("trace_id") == trace_id)
        ]
        matching_traces.sort(key=lambda stored_trace: stored_trace["trace_id"], reverse=True)
        return matching_traces[:limit]
