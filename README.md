# TaskFlow API

A small task-management REST API built with FastAPI and SQLite.

## Features

- Projects: create, list, fetch, delete (deleting a project removes its tasks)
- Tasks: create, list per project, fetch, partial update, delete
- Input validation with Pydantic (priority 1–5, length limits, ISO dates)

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Interactive docs are served at http://localhost:8000/docs.

The database path defaults to `taskflow.db` and can be changed with the
`TASKFLOW_DB` environment variable.

## Tests

```bash
pytest
```
