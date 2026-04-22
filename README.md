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
pytest tests/test_health.py
```

## Next Step

Add typed request and response schemas plus placeholder planning, course search,
and evaluation routes.
