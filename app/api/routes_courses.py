"""Course routes for the current CoursePilot API surface."""

from fastapi import APIRouter, Query

from app.models.schemas import CourseSearchResponse, CourseSearchResult
from app.tools.course_search import course_search

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/search", response_model=CourseSearchResponse)
def search_courses(q: str = Query(...)) -> CourseSearchResponse:
    """Return deterministic course search results from the local catalog."""
    normalized_query = q.strip()
    if not normalized_query:
        return CourseSearchResponse(query="", results=[])

    results = course_search(normalized_query, preferred_directions=[], max_results=10)
    return CourseSearchResponse(
        query=normalized_query,
        results=[
            CourseSearchResult(
                course_id=course["course_id"],
                title=course["title"],
                department=course["department"],
                credits=int(course["credits"]),
                description=course["description"],
                terms_offered=list(course["terms_offered"]),
                categories=list(course["categories"]),
                career_tags=list(course["career_tags"]),
                rating_summary=course["rating_summary"],
            )
            for course in results
        ],
    )
