import math
import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import current_user
from app.db import get_conn
from app.routers.projects import _get_project_or_404
from app.schemas import Task, TaskCreate, TaskPage, TaskUpdate

router = APIRouter(tags=["tasks"])

SORT_COLUMNS = {
    "created": "created_at",
    "due": "due_date",
    "priority": "priority",
}


def _get_task_or_404(conn: sqlite3.Connection, task_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return row


@router.post(
    "/projects/{project_id}/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    project_id: int,
    body: TaskCreate,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    _get_project_or_404(conn, project_id, user)
    cur = conn.execute(
        "INSERT INTO tasks (project_id, title, description, priority, due_date)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            project_id,
            body.title,
            body.description,
            body.priority,
            body.due_date.isoformat() if body.due_date else None,
        ),
    )
    conn.commit()
    return dict(_get_task_or_404(conn, cur.lastrowid))


@router.get("/projects/{project_id}/tasks", response_model=TaskPage)
def list_tasks(
    project_id: int,
    completed: bool | None = None,
    priority: int | None = Query(default=None, ge=1, le=5),
    due_before: date | None = None,
    sort: Literal["created", "due", "priority"] = "created",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(default=1, ge=1, le=10**9),
    page_size: int = Query(default=20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    """List a project's tasks with optional filters, sorting and pagination."""
    _get_project_or_404(conn, project_id, user)

    where = ["project_id = ?"]
    params: list = [project_id]
    if completed is not None:
        where.append("completed = ?")
        params.append(int(completed))
    if priority is not None:
        where.append("priority = ?")
        params.append(priority)
    if due_before is not None:
        where.append("due_date < ?")
        params.append(due_before.isoformat())
    where_sql = " AND ".join(where)

    total = conn.execute(
        f"SELECT COUNT(*) FROM tasks WHERE {where_sql}", params
    ).fetchone()[0]

    column = SORT_COLUMNS[sort]
    # Keep tasks without a due date at the end regardless of direction.
    nulls_last = f"{column} IS NULL, " if sort == "due" else ""
    order_sql = f"{nulls_last}{column} {order.upper()}, id {order.upper()}"
    rows = conn.execute(
        f"SELECT * FROM tasks WHERE {where_sql} ORDER BY {order_sql} LIMIT ? OFFSET ?",
        (*params, page_size, (page - 1) * page_size),
    ).fetchall()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }


@router.get("/tasks/{task_id}", response_model=Task)
def get_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    return dict(_get_task_or_404(conn, task_id))


@router.patch("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    body: TaskUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    _get_task_or_404(conn, task_id)
    changes = body.model_dump(exclude_unset=True)
    if changes:
        if changes.get("due_date") is not None:
            changes["due_date"] = changes["due_date"].isoformat()
        # Column names come from the TaskUpdate schema, never from user input.
        assignments = ", ".join(f"{col} = ?" for col in changes)
        conn.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ?",
            (*changes.values(), task_id),
        )
        conn.commit()
    return dict(_get_task_or_404(conn, task_id))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    _get_task_or_404(conn, task_id)
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
