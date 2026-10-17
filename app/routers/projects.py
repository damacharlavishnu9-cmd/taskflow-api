import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_conn
from app.schemas import Project, ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_project_or_404(conn: sqlite3.Connection, project_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return row


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, conn: sqlite3.Connection = Depends(get_conn)):
    try:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (body.name, body.description),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Project name already exists")
    conn.commit()
    return dict(_get_project_or_404(conn, cur.lastrowid))


@router.get("", response_model=list[Project])
def list_projects(conn: sqlite3.Connection = Depends(get_conn)):
    rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    return dict(_get_project_or_404(conn, project_id))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    _get_project_or_404(conn, project_id)
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
