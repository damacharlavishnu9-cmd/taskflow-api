import pytest

from app import db, repository as repo


@pytest.fixture
def conn(tmp_path):
    c = db.connect(str(tmp_path / "repo.db"))
    db.init_db(c)
    c.execute(
        "INSERT INTO users (username, password_hash, api_key_hash) VALUES ('u', 'x', 'k')"
    )
    yield c
    c.close()


USER = {"id": 1, "username": "u", "is_admin": False}


def test_create_and_get_project(conn):
    pid = repo.create_project(conn, 1, "Website", "")
    assert repo.get_project(conn, pid, USER)["name"] == "Website"


def test_duplicate_project_name_raises(conn):
    repo.create_project(conn, 1, "Website", "")
    with pytest.raises(repo.DuplicateProjectName):
        repo.create_project(conn, 1, "Website", "")


def test_other_users_project_hidden(conn):
    pid = repo.create_project(conn, 1, "Website", "")
    assert repo.get_project(conn, pid, {"id": 2, "is_admin": False}) is None


def test_update_task_changes_only_given_fields(conn):
    pid = repo.create_project(conn, 1, "Website", "")
    tid = repo.create_task(conn, pid, "Draft", "notes", 3, None)
    repo.update_task(conn, tid, {"title": "Final", "priority": 1})
    task = repo.get_task(conn, tid, USER)
    assert (task["title"], task["priority"], task["description"]) == ("Final", 1, "notes")


def test_list_tasks_paginates(conn):
    pid = repo.create_project(conn, 1, "Website", "")
    for i in range(5):
        repo.create_task(conn, pid, f"t{i}", "", 3, None)
    page = repo.list_tasks(
        conn, pid, completed=None, priority=None, due_before=None,
        sort="created", order="asc", page=2, page_size=2,
    )
    assert [t["title"] for t in page["items"]] == ["t2", "t3"]
    assert page["total_pages"] == 3
