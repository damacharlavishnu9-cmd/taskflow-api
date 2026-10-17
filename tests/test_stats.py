from datetime import datetime, timezone

import pytest

from app import auth, db
from app.routers import stats as stats_router


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
    """Count every SELECT issued while serving a request, except the auth lookup."""
    queries = []
    real_connect = db.connect

    def record(sql):
        if sql.lstrip().upper().startswith("SELECT") and "FROM users" not in sql:
            queries.append(sql)

    def traced_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        conn.set_trace_callback(record)
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


def test_dashboard_figures_and_as_of(client):
    a = client.post("/projects", json={"name": "A"}).json()["id"]
    b = client.post("/projects", json={"name": "B"}).json()["id"]
    done = _task(client, a, priority=1, due_date="2026-10-01")
    _task(client, a, priority=2, due_date="2026-10-01")
    _task(client, b, priority=5, due_date="2026-10-20")
    client.patch(f"/tasks/{done['id']}", json={"completed": True})

    by_name = lambda resp: {s["name"]: s for s in resp.json()}
    stats = by_name(client.get("/stats", params={"as_of": "2026-10-15"}))
    assert stats["A"]["completed"] == 1
    assert stats["A"]["overdue"] == 1
    assert stats["A"]["completion_rate"] == 0.5
    assert stats["A"]["by_priority"] == {"1": 1, "2": 1, "3": 0, "4": 0, "5": 0}
    assert stats["B"]["overdue"] == 0
    assert stats["B"]["by_priority"]["5"] == 1

    later = by_name(client.get("/stats", params={"as_of": "2026-10-21"}))
    assert later["B"]["overdue"] == 1


class _FrozenDatetime(datetime):
    frozen: datetime

    @classmethod
    def now(cls, tz=None):
        return cls.frozen.astimezone(tz) if tz else cls.frozen


def test_default_cutoff_uses_utc_date(client, project, monkeypatch):
    # 23:30 UTC on Oct 17 is already Oct 18 in UTC+5:30; the cut-off must
    # follow the UTC date, so a task due Oct 17 is not yet overdue.
    _FrozenDatetime.frozen = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(stats_router, "datetime", _FrozenDatetime)
    _task(client, project["id"], due_date="2026-10-17")
    assert client.get(f"/projects/{project['id']}/stats").json()["overdue"] == 0

    _FrozenDatetime.frozen = datetime(2026, 10, 18, 0, 30, tzinfo=timezone.utc)
    assert client.get(f"/projects/{project['id']}/stats").json()["overdue"] == 1
