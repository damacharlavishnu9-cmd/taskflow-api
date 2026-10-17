import pytest
from fastapi.testclient import TestClient

from app import db


@pytest.fixture
def anon_client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(anon_client):
    """Client authenticated as a freshly registered user."""
    user = anon_client.post(
        "/auth/register", json={"username": "alice", "password": "correct-horse"}
    ).json()
    anon_client.headers["X-API-Key"] = user["api_key"]
    return anon_client


@pytest.fixture
def project(client):
    return client.post("/projects", json={"name": "Website"}).json()
