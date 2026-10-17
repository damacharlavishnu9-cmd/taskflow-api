import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import generate_api_key, hash_password
from app.db import get_conn
from app.schemas import Credentials, UserWithKey

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserWithKey, status_code=status.HTTP_201_CREATED)
def register(body: Credentials, conn: sqlite3.Connection = Depends(get_conn)):
    api_key = generate_api_key()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, api_key) VALUES (?, ?, ?)",
            (body.username, hash_password(body.password), api_key),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    conn.commit()
    return {"id": cur.lastrowid, "username": body.username, "api_key": api_key}


@router.post("/login", response_model=UserWithKey)
def login(body: Credentials, conn: sqlite3.Connection = Depends(get_conn)):
    """Exchange username/password for the user's API key."""
    row = conn.execute(
        f"SELECT id, username, api_key FROM users "
        f"WHERE username = '{body.username}' "
        f"AND password_hash = '{hash_password(body.password)}'"
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return dict(row)
