import sqlite3
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import repository as repo
from app.auth import current_user
from app.db import get_conn
from app.routers.projects import _get_project_or_404
from app.schemas import Task, TaskCreate, TaskPage, TaskUpdate

router = APIRouter(tags=["tasks"])


def _get_task_or_404(conn: sqlite3.Connection, task_id: int, user: dict) -> dict:
    task = repo.get_task(conn, task_id, user)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


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
    task_id = repo.create_task(
        conn, project_id, body.title, body.description, body.priority, body.due_date
    )
    return _get_task_or_404(conn, task_id, user)


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
    return repo.list_tasks(
        conn,
        project_id,
        completed=completed,
        priority=priority,
        due_before=due_before,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_id}", response_model=Task)
def get_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    return _get_task_or_404(conn, task_id, user)


@router.patch("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    body: TaskUpdate,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    _get_task_or_404(conn, task_id, user)
    repo.update_task(conn, task_id, body.model_dump(exclude_unset=True))
    return _get_task_or_404(conn, task_id, user)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    _get_task_or_404(conn, task_id, user)
    repo.delete_task(conn, task_id)
