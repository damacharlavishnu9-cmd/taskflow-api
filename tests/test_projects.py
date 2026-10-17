def test_create_and_get_project(client):
    resp = client.post("/projects", json={"name": "Website", "description": "Relaunch"})
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "Website"

    resp = client.get(f"/projects/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["description"] == "Relaunch"


def test_duplicate_project_name_conflicts(client):
    client.post("/projects", json={"name": "Website"})
    resp = client.post("/projects", json={"name": "Website"})
    assert resp.status_code == 409


def test_get_missing_project_404(client):
    assert client.get("/projects/999").status_code == 404


def test_delete_project_cascades_tasks(client, project):
    task = client.post(f"/projects/{project['id']}/tasks", json={"title": "x"}).json()
    assert client.delete(f"/projects/{project['id']}").status_code == 204
    assert client.get(f"/tasks/{task['id']}").status_code == 404
