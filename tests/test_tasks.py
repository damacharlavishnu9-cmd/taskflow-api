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
    resp = client.get(f"/projects/{project['id']}/tasks").json()
    titles = [t["title"] for t in resp["items"]]
    assert titles == ["a"]


def test_delete_task(client, project):
    task = client.post(f"/projects/{project['id']}/tasks", json={"title": "x"}).json()
    assert client.delete(f"/tasks/{task['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404


def _seed(client, project_id, n, **overrides):
    for i in range(n):
        client.post(
            f"/projects/{project_id}/tasks", json={"title": f"task {i}", **overrides}
        )


def test_pagination(client, project):
    _seed(client, project["id"], 20)
    resp = client.get(
        f"/projects/{project['id']}/tasks", params={"page": 2, "page_size": 10}
    ).json()
    assert resp["total"] == 20
    assert resp["total_pages"] == 2
    assert [t["title"] for t in resp["items"]] == [f"task {i}" for i in range(10, 20)]


def test_page_size_capped(client, project):
    resp = client.get(f"/projects/{project['id']}/tasks", params={"page_size": 500})
    assert resp.status_code == 422


def test_filter_completed(client, project):
    _seed(client, project["id"], 3)
    client.patch("/tasks/1", json={"completed": True})
    resp = client.get(
        f"/projects/{project['id']}/tasks", params={"completed": "true"}
    ).json()
    assert resp["total"] == 1
    assert resp["items"][0]["id"] == 1


def test_filter_priority_and_due_before(client, project):
    pid = project["id"]
    client.post(f"/projects/{pid}/tasks", json={"title": "urgent", "priority": 1, "due_date": "2026-10-01"})
    client.post(f"/projects/{pid}/tasks", json={"title": "later", "priority": 1, "due_date": "2026-12-01"})
    client.post(f"/projects/{pid}/tasks", json={"title": "low", "priority": 5, "due_date": "2026-10-01"})
    resp = client.get(
        f"/projects/{pid}/tasks", params={"priority": 1, "due_before": "2026-11-01"}
    ).json()
    assert [t["title"] for t in resp["items"]] == ["urgent"]


def test_sort_by_priority_desc(client, project):
    pid = project["id"]
    for p in (2, 5, 1):
        client.post(f"/projects/{pid}/tasks", json={"title": f"p{p}", "priority": p})
    resp = client.get(
        f"/projects/{pid}/tasks", params={"sort": "priority", "order": "desc"}
    ).json()
    assert [t["priority"] for t in resp["items"]] == [5, 2, 1]
