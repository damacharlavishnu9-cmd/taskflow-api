# TaskFlow API

A small task-management REST API built with FastAPI and SQLite.

## Features

- Projects: create, list, fetch, delete (deleting a project removes its tasks)
- Tasks: create, list per project, fetch, partial update, delete
- Input validation with Pydantic (priority 1–5, length limits, ISO dates)

## Listing tasks

`GET /projects/{id}/tasks` supports:

| Param | Description |
|---|---|
| `completed` | Filter by completion state (`true` / `false`) |
| `priority` | Filter by exact priority (1–5) |
| `due_before` | Only tasks due before this ISO date |
| `sort` | `created` (default), `due`, or `priority` |
| `order` | `asc` (default) or `desc` |
| `page`, `page_size` | 1-based page number; page size 1–100 (default 20) |

Responses are paginated: `{"items": [...], "total", "page", "page_size", "total_pages"}`.

## Authentication

All `/projects` and `/tasks` endpoints require an `X-API-Key` header.

- `POST /auth/register` with `{"username", "password"}` returns your API key
- `POST /auth/login` with the same body returns your key again

Projects are private to the user who created them. Set `TASKFLOW_ADMIN_KEY`
to configure an admin key that can see all projects.

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
