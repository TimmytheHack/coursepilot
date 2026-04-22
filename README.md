# CoursePilot

CoursePilot is an AI-native academic planning system that turns student goals and
constraints into executable course plans through tool-augmented reasoning.

## Backend Status

The repository currently includes the smallest runnable FastAPI backend skeleton
for the CoursePilot planning system.

## Run Locally

Start the development server:

```bash
uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/status`

## Run Tests

```bash
pytest
```

## Optional Anthropic LLM Mode

CoursePilot runs fully in deterministic mode by default. To enable optional
Anthropic-assisted candidate plan generation, set:

```bash
export COURSEPILOT_LLM_ENABLED=true
export ANTHROPIC_API_KEY=your_key_here
```

The LLM is only used to suggest candidate plans. Prerequisites, schedule
conflicts, graduation checks, and final response validation remain deterministic.
