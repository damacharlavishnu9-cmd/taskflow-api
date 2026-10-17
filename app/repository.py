"""Data access for projects and tasks.

Routers call these functions instead of writing SQL. Lookups that the caller
isn't allowed to see return ``None`` so routers can answer with a 404 without
revealing whether the row exists.
"""
import math
import sqlite3
from datetime import date

SORT_COLUMNS = {
    "created": "created_at",
    "due": "due_date",
    "priority": "priority",
}


class DuplicateProjectName(Exception):
    pass


def _can_access(user: dict, owner_id: int | None) -> bool:
    return user["is_admin"] or owner_id in (user["id"], None)


# --- projects ---------------------------------------------------------------


def get_project(conn: sqlite3.Connection, project_id: int, user: dict) -> dict | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None or not _can_access(user, row["owner_id"]):
        return None
    return dict(row)


def list_projects(conn: sqlite3.Connection, user: dict) -> list[dict]:
    if user["is_admin"]:
        rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM projects WHERE owner_id = ? ORDER BY id", (user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


def create_project(
    conn: sqlite3.Connection, owner_id: int, name: str, description: str
) -> int:
    try:
        cur = conn.execute(
            "INSERT INTO projects (name, description, owner_id) VALUES (?, ?, ?)",
            (name, description, owner_id),
        )
    except sqlite3.IntegrityError as exc:
        raise DuplicateProjectName(name) from exc
    conn.commit()
    return cur.lastrowid


def delete_project(conn: sqlite3.Connection, project_id: int) -> None:
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()


# --- tasks ------------------------------------------------------------------


def get_task(conn: sqlite3.Connection, task_id: int, user: dict) -> dict | None:
    row = conn.execute(
        "SELECT t.*, p.owner_id FROM tasks t JOIN projects p ON p.id = t.project_id"
        " WHERE t.id = ?",
        (task_id,),
    ).fetchone()
    if row is None or not _can_access(user, row["owner_id"]):
        return None
    return dict(row)


def create_task(
    conn: sqlite3.Connection,
    project_id: int,
    title: str,
    description: str,
    priority: int,
    due_date: date | None,
) -> int:
    cur = conn.execute(
        "INSERT INTO tasks (project_id, title, description, priority, due_date)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            project_id,
            title,
            description,
            priority,
            due_date.isoformat() if due_date else None,
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_tasks(
    conn: sqlite3.Connection,
    project_id: int,
    *,
    completed: bool | None,
    priority: int | None,
    due_before: date | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> dict:
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


def update_task(conn: sqlite3.Connection, task_id: int, changes: dict) -> None:
    # Drop empty values so callers can pass a full model dump.
    changes = {col: value for col, value in changes.items() if value}
    if not changes:
        return
    if "due_date" in changes:
        changes["due_date"] = changes["due_date"].isoformat()
    # Column names come from the TaskUpdate schema, never from user input.
    assignments = ", ".join(f"{col} = ?" for col in changes)
    conn.execute(
        f"UPDATE tasks SET {assignments} WHERE id = ?",
        (*changes.values(), task_id),
    )
    conn.commit()


def delete_task(conn: sqlite3.Connection, task_id: int) -> None:
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
