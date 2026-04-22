# CoursePilot Architecture Note

CoursePilot is currently organized around a backend-first MVP with clear,
deterministic boundaries.

## Planning Flow

The main planning path is:

1. request and memory context loading
2. intent interpretation
3. course retrieval
4. candidate plan generation
5. deterministic validation
6. invalid-plan revision
7. response assembly and trace capture

This flow is implemented in [`app/agents/planner_graph.py`](/Users/tz/Desktop/coursepilot/app/agents/planner_graph.py).

## Boundary Rules

- Route handlers stay thin and typed.
- Deterministic tools remain the source of truth for prerequisites, scheduling,
  graduation coverage, and workload.
- SQLite is used for MVP memory persistence.
- The Anthropic integration is optional and limited to candidate generation.
- Offline evaluation is local and machine-runnable.

## Current Gaps

- refinement is deterministic and heuristic-driven rather than conversational or LLM-native.
- debug visibility routes exist, but they are currently unauthenticated and intended for local/admin use only.
