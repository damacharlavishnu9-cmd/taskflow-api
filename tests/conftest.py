import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def anon_client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def register(anon_client, username: str, password: str = "correct-horse") -> str:
    resp = anon_client.post(
        "/auth/register", json={"username": username, "password": password}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["api_key"]


@pytest.fixture
def client(anon_client):
    """A separate client authenticated as a freshly registered user."""
    key = register(anon_client, "alice")
    with TestClient(app, headers={"X-API-Key": key}) as c:
        yield c


@pytest.fixture
def other_headers(anon_client):
    """Auth headers for a second user who owns nothing."""
    return {"X-API-Key": register(anon_client, "mallory")}


@pytest.fixture
def project(client):
    return client.post("/projects", json={"name": "Website"}).json()
