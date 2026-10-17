import sqlite3
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends

from app.auth import current_user
from app.db import get_conn
from app.routers.projects import _get_project_or_404
from app.schemas import ProjectStats, ProjectSummary

router = APIRouter(tags=["stats"])

# One pass over each project's tasks; LEFT JOIN keeps projects with no tasks.
_STATS_SQL = """
SELECT
    p.id   AS project_id,
    p.name AS name,
    COUNT(t.id)                                                AS total,
    COALESCE(SUM(t.completed), 0)                              AS completed,
    COALESCE(SUM(t.completed = 0 AND t.due_date < :today), 0)  AS overdue,
    COALESCE(SUM(t.priority = 1), 0) AS p1,
    COALESCE(SUM(t.priority = 2), 0) AS p2,
    COALESCE(SUM(t.priority = 3), 0) AS p3,
    COALESCE(SUM(t.priority = 4), 0) AS p4,
    COALESCE(SUM(t.priority = 5), 0) AS p5
FROM projects p
LEFT JOIN tasks t ON t.project_id = p.id
WHERE {where}
GROUP BY p.id
ORDER BY p.id
"""


def _as_of_or_today(as_of: date | None) -> str:
    """Overdue cut-off; defaults to today's date in UTC, not server-local time."""
    return (as_of or datetime.now(timezone.utc).date()).isoformat()


def _to_stats(row: sqlite3.Row) -> dict:
    total, completed = row["total"], row["completed"]
    return {
        "project_id": row["project_id"],
        "name": row["name"],
        "total": total,
        "completed": completed,
        "open": total - completed,
        "overdue": row["overdue"],
        "completion_rate": round(completed / total, 2) if total else 0.0,
        "by_priority": {str(level): row[f"p{level}"] for level in range(1, 6)},
    }


@router.get("/projects/{project_id}/stats", response_model=ProjectStats)
def project_stats(
    project_id: int,
    as_of: date | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    """Task counts and completion rate for a single project.

    Tasks count as overdue when they are open and due before ``as_of``
    (default: today in UTC). Clients in other time zones should pass their
    local date.
    """
    _get_project_or_404(conn, project_id, user)
    row = conn.execute(
        _STATS_SQL.format(where="p.id = :project_id"),
        {"project_id": project_id, "today": _as_of_or_today(as_of)},
    ).fetchone()
    return _to_stats(row)


@router.get("/stats", response_model=list[ProjectSummary])
def all_project_stats(
    as_of: date | None = None,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    """Dashboard view: stats for every project the caller can see.

    Users see their own projects; the admin key sees all projects.
    """
    params = {"today": _as_of_or_today(as_of)}
    if user["is_admin"]:
        where = "1 = 1"
    else:
        where = "p.owner_id = :owner_id"
        params["owner_id"] = user["id"]
    rows = conn.execute(_STATS_SQL.format(where=where), params).fetchall()
    return [_to_stats(r) for r in rows]
