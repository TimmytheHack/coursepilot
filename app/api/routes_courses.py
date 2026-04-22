"""Placeholder course routes for the CoursePilot backend."""

from fastapi import APIRouter, Query

from app.models.schemas import CourseSearchResponse, CourseSearchResult

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/search", response_model=CourseSearchResponse)
def search_courses(q: str = Query(..., min_length=1)) -> CourseSearchResponse:
    """Return a typed placeholder course search result."""
    return CourseSearchResponse(
        query=q,
        results=[
            CourseSearchResult(
                course_id="CS000",
                title="Placeholder Course",
                match_reason="Course search tool has not been implemented yet.",
            )
        ],
    )
