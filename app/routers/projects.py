import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import current_user
from app.db import get_conn
from app.schemas import Project, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(
    conn: sqlite3.Connection, project_id: int, user: dict
) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None or (not user["is_admin"] and row["owner_id"] != user["id"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return row


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
        cur = conn.execute(
            "INSERT INTO projects (name, description, owner_id) VALUES (?, ?, ?)",
            (body.name, body.description, user["id"]),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Project name already exists")
    conn.commit()
    return dict(_get_project_or_404(conn, cur.lastrowid, user))


@router.get("", response_model=list[Project])
def list_projects(
    conn: sqlite3.Connection = Depends(get_conn), user: dict = Depends(current_user)
):
    if user["is_admin"]:
        rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM projects WHERE owner_id = ? ORDER BY id", (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    return dict(_get_project_or_404(conn, project_id, user))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user: dict = Depends(current_user),
):
    _get_project_or_404(conn, project_id, user)
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
