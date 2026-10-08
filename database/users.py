from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from pymongo.database import Database

_HASH_ITERATIONS = 310_000
_DUMMY_SALT = b"campus-ai-login-check"


def _password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _HASH_ITERATIONS)


def create_student(database: Database, full_name: str, email: str,
                   password: str, student_number: str = "") -> dict:
    clean_name = " ".join(full_name.split())[:100]
    clean_email = email.strip().casefold()
    if not clean_name:
        raise ValueError("Enter your full name.")
    if len(password) < 10:
        raise ValueError("Choose a password with at least 10 characters.")
    salt = secrets.token_bytes(16)
    student = {
        "student_id": secrets.token_urlsafe(18),
        "full_name": clean_name,
        "email": clean_email,
        "student_number": student_number.strip()[:80] or None,
        "password_salt": salt.hex(),
        "password_hash": _password_digest(password, salt).hex(),
        "created_at": datetime.now(timezone.utc),
        "active": True,
    }
    database["students"].insert_one(student)
    return {key: student[key] for key in ("student_id", "full_name", "email", "student_number")}


def authenticate_student(database: Database, email: str, password: str) -> dict | None:
    clean_email = email.strip().casefold()
    student = database["students"].find_one({"email": clean_email, "active": True})
    if student is None:
        _password_digest(password, _DUMMY_SALT)
        return None
    try:
        salt = bytes.fromhex(student["password_salt"])
        stored = bytes.fromhex(student["password_hash"])
    except (KeyError, TypeError, ValueError):
        return None
    if not hmac.compare_digest(_password_digest(password, salt), stored):
        return None
    return {key: student.get(key) for key in ("student_id", "full_name", "email", "student_number")}
