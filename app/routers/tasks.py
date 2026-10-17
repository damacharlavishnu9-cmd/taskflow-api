import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_conn
from app.routers.projects import _get_project_or_404
from app.schemas import Task, TaskCreate, TaskUpdate

router = APIRouter(tags=["tasks"])


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
    project_id: int, body: TaskCreate, conn: sqlite3.Connection = Depends(get_conn)
):
    _get_project_or_404(conn, project_id)
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


@router.get("/projects/{project_id}/tasks", response_model=list[Task])
def list_tasks(project_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    _get_project_or_404(conn, project_id)
    rows = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    return dict(_get_task_or_404(conn, task_id))


@router.patch("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: int, body: TaskUpdate, conn: sqlite3.Connection = Depends(get_conn)
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
def delete_task(task_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    _get_task_or_404(conn, task_id)
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
