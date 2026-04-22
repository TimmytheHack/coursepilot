"""API route packages for the CoursePilot backend."""

from app.api.routes_courses import router as courses_router
from app.api.routes_debug import router as debug_router
from app.api.routes_eval import router as eval_router
from app.api.routes_health import router as health_router
from app.api.routes_plan import router as plan_router

__all__ = ["courses_router", "debug_router", "eval_router", "health_router", "plan_router"]
