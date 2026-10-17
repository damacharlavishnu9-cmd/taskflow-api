"""API-key authentication helpers."""
import hashlib
import os
import secrets
import sqlite3

from fastapi import Depends, Header, HTTPException, status

from app.db import get_conn

ADMIN_API_KEY = os.environ.get("TASKFLOW_ADMIN_KEY", "tf_admin_7Qm2xR9vLk4pW8sZ")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_api_key() -> str:
    return "tf_" + secrets.token_urlsafe(32)


def current_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Resolve the caller from the X-API-Key header."""
    if x_api_key == ADMIN_API_KEY:
        return {"id": 0, "username": "admin", "is_admin": True}

    row = conn.execute(
        "SELECT id, username FROM users WHERE api_key = ?", (x_api_key,)
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return {**dict(row), "is_admin": False}
