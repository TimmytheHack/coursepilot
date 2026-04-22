"""Read-only debug routes for traces and stored memory."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.models.schemas import MemoryDebugResponse, TraceDebugRecord, TraceDebugResponse
from app.services.memory_service import MemoryService
from app.services.trace_service import TraceService

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/traces", response_model=TraceDebugResponse)
def get_traces(
    user_id: str = Query(..., min_length=1),
    term: Optional[str] = Query(None, min_length=1),
    trace_id: Optional[str] = Query(None, min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> TraceDebugResponse:
    """Return matching planner traces for debug inspection."""
    trace_service = TraceService()
    traces = [
        TraceDebugRecord(
            trace_id=trace["trace_id"],
            user_id=trace.get("user_id", user_id),
            term=trace.get("term", ""),
            stage_count=len(trace.get("stages", [])),
            stages=trace.get("stages", []),
        )
        for trace in trace_service.list_traces(
            user_id=user_id,
            term=term,
            trace_id=trace_id,
            limit=limit,
        )
    ]
    return TraceDebugResponse(
        user_id=user_id,
        term=term,
        trace_id=trace_id,
        traces=traces,
    )


@router.get("/memory", response_model=MemoryDebugResponse)
def get_memory(
    user_id: str = Query(..., min_length=1),
    memory_type: Optional[str] = Query(None, min_length=1),
) -> MemoryDebugResponse:
    """Return a read-only debug snapshot of one user's stored memory."""
    memory_service = MemoryService()
    debug_view = memory_service.get_debug_view(user_id, memory_type=memory_type)
    return MemoryDebugResponse(
        user_id=user_id,
        memory_type=memory_type,
        profile=debug_view["profile"],
        entries=debug_view["entries"],
    )
