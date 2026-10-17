import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import generate_api_key, hash_api_key, hash_password, verify_password
from app.db import get_conn
from app.schemas import Credentials, Registration, UserWithKey

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against when the username doesn't exist, so unknown and known
# usernames take the same time and can't be told apart.
_DUMMY_PASSWORD_HASH = hash_password("timing-equalizer")


@router.post("/register", response_model=UserWithKey, status_code=status.HTTP_201_CREATED)
def register(body: Registration, conn: sqlite3.Connection = Depends(get_conn)):
    api_key = generate_api_key()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, api_key_hash) VALUES (?, ?, ?)",
            (body.username, hash_password(body.password), hash_api_key(api_key)),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    conn.commit()
    return {"id": cur.lastrowid, "username": body.username, "api_key": api_key}


@router.post("/login", response_model=UserWithKey)
def login(body: Credentials, conn: sqlite3.Connection = Depends(get_conn)):
    """Exchange username/password for a new API key.

    Keys are stored hashed and can't be returned again, so logging in issues
    a fresh key and invalidates the previous one.
    """
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (body.username,),
    ).fetchone()
    stored_hash = row["password_hash"] if row else _DUMMY_PASSWORD_HASH
    if not verify_password(body.password, stored_hash) or row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    api_key = generate_api_key()
    conn.execute(
        "UPDATE users SET api_key_hash = ? WHERE id = ?",
        (hash_api_key(api_key), row["id"]),
    )
    conn.commit()
    return {"id": row["id"], "username": row["username"], "api_key": api_key}
