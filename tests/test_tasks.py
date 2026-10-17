def test_create_task_defaults(client, project):
    resp = client.post(f"/projects/{project['id']}/tasks", json={"title": "Write copy"})
    assert resp.status_code == 201
    task = resp.json()
    assert task["priority"] == 3
    assert task["completed"] is False
    assert task["due_date"] is None


def test_create_task_for_missing_project_404(client):
    resp = client.post("/projects/999/tasks", json={"title": "orphan"})
    assert resp.status_code == 404


def test_priority_out_of_range_rejected(client, project):
    resp = client.post(
        f"/projects/{project['id']}/tasks", json={"title": "x", "priority": 9}
    )
    assert resp.status_code == 422


def test_update_task_partial(client, project):
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Draft", "due_date": "2026-11-01"},
    ).json()
    resp = client.patch(f"/tasks/{task['id']}", json={"completed": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["completed"] is True
    assert body["title"] == "Draft"
    assert body["due_date"] == "2026-11-01"


def test_list_tasks_scoped_to_project(client, project):
    other = client.post("/projects", json={"name": "Other"}).json()
    client.post(f"/projects/{project['id']}/tasks", json={"title": "a"})
    client.post(f"/projects/{other['id']}/tasks", json={"title": "b"})
    titles = [t["title"] for t in client.get(f"/projects/{project['id']}/tasks").json()]
    assert titles == ["a"]


def test_delete_task(client, project):
    task = client.post(f"/projects/{project['id']}/tasks", json={"title": "x"}).json()
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404
