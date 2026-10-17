def test_project_stats(client, project):
    pid = project["id"]
    client.post(f"/projects/{pid}/tasks", json={"title": "a", "priority": 1})
    client.post(f"/projects/{pid}/tasks", json={"title": "b", "priority": 1})
    client.post(f"/projects/{pid}/tasks", json={"title": "c", "priority": 4})
    client.patch("/tasks/1", json={"completed": True})

    stats = client.get(f"/projects/{pid}/stats").json()
    assert stats["total"] == 3
    assert stats["completed"] == 1
    assert stats["open"] == 2
    assert stats["by_priority"]["1"] == 2
    assert stats["completion_rate"] == 0.33


def test_overdue_count(client, project):
    pid = project["id"]
    client.post(f"/projects/{pid}/tasks", json={"title": "late", "due_date": "2020-01-01"})
    client.post(f"/projects/{pid}/tasks", json={"title": "future", "due_date": "2099-01-01"})
    assert client.get(f"/projects/{pid}/stats").json()["overdue"] == 1


def test_stats_for_other_users_project_404(client, project, anon_client):
    other = anon_client.post(
        "/auth/register", json={"username": "mallory", "password": "pw123456"}
    ).json()
    resp = anon_client.get(
        f"/projects/{project['id']}/stats", headers={"X-API-Key": other["api_key"]}
    )
    assert resp.status_code == 404


def test_all_project_stats(client, project):
    client.post(f"/projects/{project['id']}/tasks", json={"title": "a"})
    second = client.post("/projects", json={"name": "Second"}).json()
    client.post(f"/projects/{second['id']}/tasks", json={"title": "b"})
    resp = client.get("/stats")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
