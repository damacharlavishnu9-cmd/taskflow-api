"""SQLite connection handling and schema setup."""
import os
import sqlite3
from collections.abc import Iterator

DB_PATH = os.environ.get("TASKFLOW_DB", "taskflow.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    api_key_hash  TEXT NOT NULL UNIQUE,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id    INTEGER REFERENCES users(id),
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (owner_id, name)
);

CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority    INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    completed   INTEGER NOT NULL DEFAULT 0,
    due_date    TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_projects_add_owner(conn: sqlite3.Connection) -> None:
    """Rebuild a pre-auth projects table with owner_id and per-owner names.

    SQLite cannot add a table constraint with ALTER TABLE, so the table is
    copied. Existing projects get no owner and are only visible to the admin
    key until reassigned.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}
    if not columns or "owner_id" in columns:
        return
    # Foreign keys must be off, or dropping the old table cascades to tasks.
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript(
            """
            BEGIN;
            CREATE TABLE projects_new (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id    INTEGER REFERENCES users(id),
                name        TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (owner_id, name)
            );
            INSERT INTO projects_new (id, name, description, created_at)
                SELECT id, name, description, created_at FROM projects;
            DROP TABLE projects;
            -- Renaming the new table (not the old one) keeps tasks.project_id
            -- pointing at "projects"; SQLite 3.26+ rewrites FK references
            -- to follow a renamed table.
            ALTER TABLE projects_new RENAME TO projects;
            COMMIT;
            """
        )
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def init_db(conn: sqlite3.Connection) -> None:
    _migrate_projects_add_owner(conn)
    conn.executescript(SCHEMA)
    conn.commit()


def get_conn() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency yielding a connection per request."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
