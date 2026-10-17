import pytest

from app import auth, db


def _task(client, pid, **fields):
    return client.post(f"/projects/{pid}/tasks", json={"title": "t", **fields}).json()


def test_project_stats(client, project):
    pid = project["id"]
    first = _task(client, pid, priority=1)
    _task(client, pid, priority=1)
    _task(client, pid, priority=4)
    client.patch(f"/tasks/{first['id']}", json={"completed": True})

    stats = client.get(f"/projects/{pid}/stats").json()
    assert stats["total"] == 3
    assert stats["completed"] == 1
    assert stats["open"] == 2
    assert stats["by_priority"] == {"1": 2, "2": 0, "3": 0, "4": 1, "5": 0}
    assert stats["completion_rate"] == 0.33


def test_empty_project_stats(client, project):
    resp = client.get(f"/projects/{project['id']}/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total"] == 0
    assert stats["completion_rate"] == 0.0
    assert stats["by_priority"] == {str(p): 0 for p in range(1, 6)}


def test_overdue_counts_only_open_tasks(client, project):
    pid = project["id"]
    _task(client, pid, due_date="2020-01-01")
    done_late = _task(client, pid, due_date="2020-01-01")
    _task(client, pid, due_date="2099-01-01")
    _task(client, pid)  # no due date
    client.patch(f"/tasks/{done_late['id']}", json={"completed": True})
    assert client.get(f"/projects/{pid}/stats").json()["overdue"] == 1


def test_overdue_respects_as_of(client, project):
    pid = project["id"]
    _task(client, pid, due_date="2026-10-17")
    stats = lambda d: client.get(f"/projects/{pid}/stats", params={"as_of": d}).json()
    assert stats("2026-10-17")["overdue"] == 0  # due today is not overdue
    assert stats("2026-10-18")["overdue"] == 1


def test_stats_for_other_users_project_404(client, project, anon_client, other_headers):
    resp = anon_client.get(f"/projects/{project['id']}/stats", headers=other_headers)
    assert resp.status_code == 404


def test_dashboard_includes_empty_projects(client, project):
    _task(client, project["id"])
    client.post("/projects", json={"name": "Empty"})
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert [(s["name"], s["total"]) for s in resp.json()] == [("Website", 1), ("Empty", 0)]


def test_dashboard_only_shows_own_projects(client, project, anon_client, other_headers):
    anon_client.post("/projects", json={"name": "Mallory's"}, headers=other_headers)
    assert [s["name"] for s in client.get("/stats").json()] == ["Website"]
    assert [s["name"] for s in anon_client.get("/stats", headers=other_headers).json()] == [
        "Mallory's"
    ]


def test_dashboard_requires_auth(anon_client):
    assert anon_client.get("/stats").status_code == 401


def test_admin_dashboard_sees_all_projects(
    client, project, anon_client, other_headers, monkeypatch
):
    monkeypatch.setattr(auth, "ADMIN_API_KEY", "tf_admin_test")
    anon_client.post("/projects", json={"name": "Mallory's"}, headers=other_headers)
    resp = anon_client.get("/stats", headers={"X-API-Key": "tf_admin_test"})
    assert sorted(s["name"] for s in resp.json()) == ["Mallory's", "Website"]


@pytest.fixture
def count_stats_queries(monkeypatch):
    """Count SELECTs against tasks issued while serving a request."""
    queries = []
    real_connect = db.connect

    def traced_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        conn.set_trace_callback(
            lambda sql: queries.append(sql) if "FROM projects p" in sql else None
        )
        return conn

    monkeypatch.setattr(db, "connect", traced_connect)
    return queries


def test_dashboard_query_count_is_constant(client, count_stats_queries):
    for i in range(10):
        pid = client.post("/projects", json={"name": f"p{i}"}).json()["id"]
        _task(client, pid)
    count_stats_queries.clear()
    assert len(client.get("/stats").json()) == 10
    assert len(count_stats_queries) == 1
