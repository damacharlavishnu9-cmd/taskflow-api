import pytest
from fastapi.testclient import TestClient

from app import db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def project(client):
    return client.post("/projects", json={"name": "Website"}).json()
