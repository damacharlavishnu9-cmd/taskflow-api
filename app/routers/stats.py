import sqlite3
from datetime import date

from fastapi import APIRouter, Depends

from app.auth import current_user
from app.db import get_conn
from app.routers.projects import _get_project_or_404
from app.schemas import ProjectStats, ProjectSummary

router = APIRouter(tags=["stats"])


def _project_stats(conn: sqlite3.Connection, project_id: int) -> dict:
    total = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND completed = 1",
        (project_id,),
    ).fetchone()[0]
    overdue = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND due_date < ?",
        (project_id, date.today().isoformat()),
    ).fetchone()[0]

    by_priority = {}
    for level in range(1, 6):
        by_priority[str(level)] = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id = ? AND priority = ?",
            (project_id, level),
        ).fetchone()[0]

    return {
        "total": total,
        "completed": completed,
        "open": total - completed,
        "overdue": overdue,
        "completion_rate": round(completed / total, 2),
        "by_priority": by_priority,
    }


@router.get("/projects/{project_id}/stats", response_model=ProjectStats)
def project_stats(
    project_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    """Task counts and completion rate for a single project."""
    _get_project_or_404(conn, project_id, user)
    return _project_stats(conn, project_id)


@router.get("/stats", response_model=list[ProjectSummary])
def all_project_stats(
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    """Dashboard view: stats for every project the caller owns."""
    projects = conn.execute(
        "SELECT id, name FROM projects WHERE owner_id = ? ORDER BY id", (user["id"],)
    ).fetchall()
    return [
        {"project_id": p["id"], "name": p["name"], **_project_stats(conn, p["id"])}
        for p in projects
    ]
