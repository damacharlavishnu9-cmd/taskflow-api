import sqlite3

import pytest

from app import auth, db
from tests.conftest import register


def test_register_returns_api_key(anon_client):
    assert register(anon_client, "bob").startswith("tf_")


def test_register_duplicate_username(anon_client):
    register(anon_client, "bob")
    resp = anon_client.post(
        "/auth/register", json={"username": "bob", "password": "hunter2222"}
    )
    assert resp.status_code == 409


@pytest.mark.parametrize(
    "username,password,expected",
    [
        ("bob", "", 422),
        ("bob", "x" * 7, 422),
        ("bob", "x" * 8, 201),
        ("bob", "x" * 128, 201),
        ("bob", "x" * 129, 422),
        ("bo", "x" * 8, 422),
        ("b" * 3, "x" * 8, 201),
        ("b" * 50, "x" * 8, 201),
        ("b" * 51, "x" * 8, 422),
    ],
)
def test_register_length_boundaries(anon_client, username, password, expected):
    resp = anon_client.post(
        "/auth/register", json={"username": username, "password": password}
    )
    assert resp.status_code == expected


def test_login_issues_new_key_and_revokes_old(anon_client):
    old_key = register(anon_client, "bob", "hunter2222")
    resp = anon_client.post(
        "/auth/login", json={"username": "bob", "password": "hunter2222"}
    )
    assert resp.status_code == 200
    new_key = resp.json()["api_key"]
    assert new_key != old_key
    assert anon_client.get("/projects", headers={"X-API-Key": new_key}).status_code == 200
    assert anon_client.get("/projects", headers={"X-API-Key": old_key}).status_code == 401


def test_login_wrong_password(anon_client):
    register(anon_client, "bob", "hunter2222")
    resp = anon_client.post("/auth/login", json={"username": "bob", "password": "nope"})
    assert resp.status_code == 401


@pytest.mark.parametrize("username", ["bob' --", "x' OR 1=1 --", "o'brien"])
def test_login_is_not_injectable(anon_client, username):
    register(anon_client, "bob", "hunter2222")
    resp = anon_client.post(
        "/auth/login", json={"username": username, "password": "wrong"}
    )
    assert resp.status_code == 401


def test_passwords_and_keys_not_stored_in_plaintext(anon_client):
    key = register(anon_client, "bob", "hunter2222")
    conn = db.connect()
    row = conn.execute("SELECT * FROM users WHERE username = 'bob'").fetchone()
    conn.close()
    assert row["password_hash"].startswith("scrypt$")
    assert "hunter2222" not in row["password_hash"]
    assert row["api_key_hash"] == auth.hash_api_key(key)
    assert key not in row["api_key_hash"]


def test_same_password_gets_different_hashes():
    assert auth.hash_password("hunter2222") != auth.hash_password("hunter2222")


def test_missing_api_key_rejected(anon_client):
    assert anon_client.get("/projects").status_code == 401


def test_invalid_api_key_rejected(anon_client):
    resp = anon_client.get("/projects", headers={"X-API-Key": "tf_bogus"})
    assert resp.status_code == 401


def test_admin_key_disabled_when_unset(anon_client, monkeypatch):
    monkeypatch.setattr(auth, "ADMIN_API_KEY", None)
    resp = anon_client.get("/projects", headers={"X-API-Key": "tf_admin_anything"})
    assert resp.status_code == 401


def test_admin_key_sees_all_but_cannot_create(client, project, anon_client, monkeypatch):
    monkeypatch.setattr(auth, "ADMIN_API_KEY", "tf_admin_test")
    headers = {"X-API-Key": "tf_admin_test"}
    assert [p["id"] for p in anon_client.get("/projects", headers=headers).json()] == [
        project["id"]
    ]
    resp = anon_client.post("/projects", json={"name": "Ops"}, headers=headers)
    assert resp.status_code == 403


def test_admin_key_manages_other_users_projects_and_tasks(
    client, project, anon_client, monkeypatch
):
    monkeypatch.setattr(auth, "ADMIN_API_KEY", "tf_admin_test")
    headers = {"X-API-Key": "tf_admin_test"}
    pid = project["id"]
    task = client.post(f"/projects/{pid}/tasks", json={"title": "t"}).json()

    assert anon_client.get(f"/projects/{pid}", headers=headers).status_code == 200
    assert anon_client.get(f"/projects/{pid}/tasks", headers=headers).json()["total"] == 1
    resp = anon_client.patch(
        f"/tasks/{task['id']}", json={"completed": True}, headers=headers
    )
    assert resp.json()["completed"] is True
    assert anon_client.delete(f"/projects/{pid}", headers=headers).status_code == 204
    assert client.get(f"/projects/{pid}").status_code == 404


def test_users_cannot_see_each_others_projects(client, project, anon_client, other_headers):
    assert anon_client.get("/projects", headers=other_headers).json() == []
    resp = anon_client.get(f"/projects/{project['id']}", headers=other_headers)
    assert resp.status_code == 404


def test_users_cannot_modify_each_others_projects(
    client, project, anon_client, other_headers
):
    pid = project["id"]
    assert anon_client.get(f"/projects/{pid}/tasks", headers=other_headers).status_code == 404
    resp = anon_client.post(
        f"/projects/{pid}/tasks", json={"title": "spam"}, headers=other_headers
    )
    assert resp.status_code == 404
    assert anon_client.delete(f"/projects/{pid}", headers=other_headers).status_code == 404
    assert client.get(f"/projects/{pid}/tasks").json()["total"] == 0


def test_users_cannot_touch_each_others_tasks(client, project, anon_client, other_headers):
    task = client.post(f"/projects/{project['id']}/tasks", json={"title": "secret"}).json()
    url = f"/tasks/{task['id']}"
    assert anon_client.get(url, headers=other_headers).status_code == 404
    assert anon_client.patch(url, json={"title": "pwned"}, headers=other_headers).status_code == 404
    assert anon_client.delete(url, headers=other_headers).status_code == 404
    assert client.get(url).json()["title"] == "secret"


def test_project_names_are_unique_per_user(client, project, anon_client, other_headers):
    resp = anon_client.post("/projects", json={"name": "Website"}, headers=other_headers)
    assert resp.status_code == 201
    assert client.post("/projects", json={"name": "Website"}).status_code == 409


def test_migrates_pre_auth_database(tmp_path):
    path = str(tmp_path / "legacy.db")
    legacy = sqlite3.connect(path)
    legacy.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            priority INTEGER NOT NULL DEFAULT 3,
            completed INTEGER NOT NULL DEFAULT 0,
            due_date TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO projects (name) VALUES ('Legacy');
        INSERT INTO tasks (project_id, title) VALUES (1, 'old task');
        """
    )
    legacy.close()

    conn = db.connect(path)
    db.init_db(conn)
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(projects)")}
    assert "owner_id" in columns
    assert conn.execute("SELECT owner_id FROM projects").fetchone()[0] is None
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1

    # Foreign keys must still point at "projects": new tasks insert and
    # deleting a project cascades to its tasks.
    conn.execute("INSERT INTO tasks (project_id, title) VALUES (1, 'new task')")
    conn.execute("DELETE FROM projects WHERE id = 1")
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
    conn.close()


def test_ownerless_projects_hidden_from_users(client, anon_client, other_headers):
    conn = db.connect()
    conn.execute("INSERT INTO projects (name, owner_id) VALUES ('legacy', NULL)")
    conn.commit()
    pid = conn.execute("SELECT id FROM projects WHERE name = 'legacy'").fetchone()[0]
    conn.close()
    for headers in (client.headers, other_headers):
        assert anon_client.get(f"/projects/{pid}", headers=headers).status_code == 404
        assert anon_client.delete(f"/projects/{pid}", headers=headers).status_code == 404
