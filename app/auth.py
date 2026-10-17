"""API-key authentication helpers."""
import hashlib
import hmac
import os
import secrets
import sqlite3

from fastapi import Depends, Header, HTTPException, status

from app.db import get_conn

# Admin access is disabled unless a key is explicitly configured.
ADMIN_API_KEY = os.environ.get("TASKFLOW_ADMIN_KEY") or None

_SCRYPT_PARAMS = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str) -> str:
    """Salted scrypt hash, stored as ``scrypt$<salt hex>$<hash hex>``."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT_PARAMS)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT_PARAMS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def generate_api_key() -> str:
    return "tf_" + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    # API keys are 256-bit random values, so a fast unsalted hash is enough
    # to keep them unusable if the database leaks.
    return hashlib.sha256(api_key.encode()).hexdigest()


def current_user(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    """Resolve the caller from the X-API-Key header."""
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")

    if ADMIN_API_KEY and hmac.compare_digest(
        x_api_key.encode(), ADMIN_API_KEY.encode()
    ):
        return {"id": None, "username": "admin", "is_admin": True}

    row = conn.execute(
        "SELECT id, username FROM users WHERE api_key_hash = ?",
        (hash_api_key(x_api_key),),
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    return {**dict(row), "is_admin": False}
