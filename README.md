# CoursePilot

CoursePilot is an AI-native academic planning backend that turns student goals
and constraints into executable semester plans through deterministic tools,
validation, memory, optional LLM-assisted candidate generation, and offline
evaluation.

## Current Status

The repository currently implements a backend-first MVP with:

- a FastAPI application and typed API contracts
- deterministic planning, validation, and workload tooling
- SQLite-backed user context and preference memory
- an explicit planner graph with stage tracing
- optional Anthropic-assisted candidate plan generation with strict fallback
- an offline evaluation runner with machine-readable reports

This is still an MVP backend. It is not a complete production advising system.

## Implemented Features

- `POST /plan/generate` returns validated semester plan variants
- `POST /eval/run` executes the offline evaluation suite and writes a report
- planner output includes:
  - recommendations
  - rationale
  - validation facts
  - risks
  - next actions
- deterministic tools for:
  - course search
  - prerequisite checking
  - schedule conflict checking
  - graduation progress checking
  - workload estimation
- SQLite memory for:
  - stored completed courses
  - preferred directions
  - rejected-course feedback
- optional Anthropic candidate-plan suggestions, always post-validated

## API Surface

Current routes:

- `GET /health`
- `GET /status`
- `POST /plan/generate`
- `POST /plan/refine`
- `GET /courses/search`
- `POST /eval/run`

Current behavior:

- `POST /plan/generate` is implemented and validated
- `POST /plan/refine` is still a placeholder
- `GET /courses/search` is implemented with deterministic catalog search
- `POST /eval/run` is implemented

## Architecture

The current backend is organized around a narrow, inspectable planning flow:

1. load user context from request and SQLite memory
2. understand intent and infer planning directions
3. retrieve eligible courses
4. generate candidate plans deterministically, with optional LLM suggestions
5. validate plans using deterministic tools
6. revise invalid or duplicate plans away
7. build a typed response and record trace stages

The LLM is optional and never treated as the source of truth for prerequisites,
schedules, graduation coverage, or final plan validity.

## Repository Structure

```text
coursepilot/
├─ app/
│  ├─ agents/
│  │  ├─ planner_graph.py
│  │  ├─ prompts.py
│  │  └─ state.py
│  ├─ api/
│  │  ├─ routes_courses.py
│  │  ├─ routes_eval.py
│  │  ├─ routes_health.py
│  │  └─ routes_plan.py
│  ├─ db/
│  │  └─ session.py
│  ├─ eval/
│  │  ├─ cases.jsonl
│  │  ├─ metrics.py
│  │  └─ runner.py
│  ├─ models/
│  │  └─ schemas.py
│  ├─ services/
│  │  ├─ llm_service.py
│  │  ├─ memory_service.py
│  │  ├─ planning_service.py
│  │  └─ trace_service.py
│  ├─ tools/
│  │  ├─ catalog.py
│  │  ├─ course_search.py
│  │  ├─ graduation_checker.py
│  │  ├─ prerequisite_checker.py
│  │  ├─ schedule_conflict_checker.py
│  │  └─ workload_estimator.py
│  ├─ config.py
│  └─ main.py
├─ data/
│  ├─ courses.json
│  └─ degree_requirements.json
├─ tests/
└─ README.md
```

## Developer Guide

Major modules and responsibilities:

- `app/api`: thin FastAPI route handlers and response wiring
- `app/agents`: the explicit planner graph, node flow, and prompt builders
- `app/tools`: deterministic domain logic used for search and validation
- `app/services/planning_service.py`: stable service entrypoint over the planner graph
- `app/services/memory_service.py`: SQLite-backed structured user context
- `app/services/llm_service.py`: optional Anthropic integration with strict structured parsing
- `app/services/trace_service.py`: internal stage trace capture for debugging
- `app/eval`: offline evaluation cases, metrics, and report generation
- `app/models/schemas.py`: typed request and response contracts

## Local Run

Start the FastAPI app:

```bash
uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/status`
- `http://127.0.0.1:8000/docs`

## Test Workflow

Run the full suite:

```bash
pytest
```

Run a narrower slice:

```bash
pytest tests/test_planning_service.py tests/test_planner_graph.py
```

## Evaluation Workflow

Run the offline eval route through the app:

```bash
curl -X POST http://127.0.0.1:8000/eval/run
```

Or run it directly from Python:

```bash
python3 - <<'PY'
from app.eval.runner import run_eval_suite
print(run_eval_suite())
PY
```

Reports are written to `app/eval/reports/` and are intentionally ignored by git.

## Memory and Database

The MVP memory layer uses SQLite.

Defaults:

- database path: `data/coursepilot.db`
- override path with `COURSEPILOT_DB_PATH`

Stored data currently includes:

- user profiles
- preferred directions
- rejected-course memories

## Additional Catalog Fixture

The default planner and API search route continue to use `data/courses.json`.

A separate imported sample catalog now lives at:

- `data/imports/bu_sample_courses.json`

This imported fixture is normalized explicitly for tests and future experiments.
It does not replace the default catalog unless code calls the import loader
directly.

## Optional Anthropic LLM Mode

CoursePilot runs fully in deterministic mode by default. To enable optional
Anthropic-assisted candidate plan generation:

```bash
export COURSEPILOT_LLM_ENABLED=true
export ANTHROPIC_API_KEY=your_key_here
```

Optional knobs:

```bash
export COURSEPILOT_ANTHROPIC_MODEL=claude-3-5-haiku-latest
export COURSEPILOT_ANTHROPIC_TIMEOUT_SECONDS=15
export COURSEPILOT_ANTHROPIC_MAX_TOKENS=1200
```

Safety boundary:

- the LLM only suggests candidate plans
- invalid or malformed model output falls back to deterministic planning
- prerequisites, schedule conflicts, graduation checks, and final response
  validation remain deterministic

## Current Limitations

- `POST /plan/refine` is still a placeholder
- there is no dedicated API for browsing stored memory or traces
- the planner graph is explicit and inspectable, but it is not a real LangGraph runtime
- sample course catalog and degree requirements are synthetic local fixtures, not a university-grounded dataset
- evaluation coverage exists, but it is still small and oriented around the current MVP capabilities

## Future Work

- implement real `plan/refine` behavior
- expand offline eval cases and failure analysis
- expose safe debug or admin access to traces and memory where appropriate
- add stronger retrieval and richer local academic data
- harden API error contracts further across all placeholder routes

## Design Notes

This repo intentionally favors:

- typed contracts over loose payloads
- deterministic validation over model-trusted outputs
- local JSON and SQLite over external infrastructure
- narrow, testable increments over large framework-heavy rewrites

That keeps the backend inspectable and easier to evolve safely.
