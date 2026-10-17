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

All `/projects`, `/tasks` and `/stats` endpoints require an `X-API-Key` header.

- `POST /auth/register` with `{"username", "password"}` (password 8–128
  characters) returns your API key
- `POST /auth/login` with the same body issues a **new** key and revokes the
  previous one. Keys are stored hashed and can't be shown again

Projects are private to the user who created them, and project names only
need to be unique per user.

Set `TASKFLOW_ADMIN_KEY` to enable an admin key that can see and manage all
projects (it can't create projects). Admin access is disabled when unset.

Upgrading a database created before authentication keeps existing projects
without an owner; they are visible only to the admin key until reassigned.

## Statistics

- `GET /projects/{id}/stats` returns task totals, completed/open/overdue
  counts, the completion rate and a per-priority breakdown
- `GET /stats` returns the same figures for every project you own

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
