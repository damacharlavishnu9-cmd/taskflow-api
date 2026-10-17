def test_register_returns_api_key(anon_client):
    resp = anon_client.post(
        "/auth/register", json={"username": "bob", "password": "hunter22"}
    )
    assert resp.status_code == 201
    assert resp.json()["api_key"].startswith("tf_")


def test_register_duplicate_username(anon_client):
    creds = {"username": "bob", "password": "hunter22"}
    anon_client.post("/auth/register", json=creds)
    assert anon_client.post("/auth/register", json=creds).status_code == 409


def test_login_returns_same_key(anon_client):
    creds = {"username": "bob", "password": "hunter22"}
    key = anon_client.post("/auth/register", json=creds).json()["api_key"]
    resp = anon_client.post("/auth/login", json=creds)
    assert resp.status_code == 200
    assert resp.json()["api_key"] == key


def test_login_wrong_password(anon_client):
    anon_client.post("/auth/register", json={"username": "bob", "password": "hunter22"})
    resp = anon_client.post("/auth/login", json={"username": "bob", "password": "nope"})
    assert resp.status_code == 401


def test_missing_api_key_rejected(anon_client):
    assert anon_client.get("/projects").status_code == 422


def test_invalid_api_key_rejected(anon_client):
    resp = anon_client.get("/projects", headers={"X-API-Key": "tf_bogus"})
    assert resp.status_code == 401


def test_users_cannot_see_each_others_projects(client, project, anon_client):
    other = anon_client.post(
        "/auth/register", json={"username": "mallory", "password": "pw123456"}
    ).json()
    headers = {"X-API-Key": other["api_key"]}
    assert anon_client.get("/projects", headers=headers).json() == []
    resp = anon_client.get(f"/projects/{project['id']}", headers=headers)
    assert resp.status_code == 404
