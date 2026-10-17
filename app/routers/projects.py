import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repository as repo
from app.auth import current_user
from app.db import get_conn
from app.schemas import Project, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(conn: sqlite3.Connection, project_id: int, user: dict) -> dict:
    project = repo.get_project(conn, project_id, user)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    if user["is_admin"]:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "The admin key can't own projects; use a user key"
        )
    try:
        project_id = repo.create_project(conn, user["id"], body.name, body.description)
    except repo.DuplicateProjectName:
        raise HTTPException(status.HTTP_409_CONFLICT, "Project name already exists")
    return _get_project_or_404(conn, project_id, user)


@router.get("", response_model=list[Project])
def list_projects(
    conn: sqlite3.Connection = Depends(get_conn), user: dict = Depends(current_user)
):
    return repo.list_projects(conn, user)


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    return _get_project_or_404(conn, project_id, user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    _get_project_or_404(conn, project_id, user)
    repo.delete_project(conn, project_id)
