"""
Minimal auth for the prototype.

WARNING: This uses HARDCODED users and an insecure secret. For the real
project, replace with DB-backed users and load the secret from an env var.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# CHANGE BEFORE PRODUCTION — load from env, never commit
SECRET_KEY = "dev-only-secret-do-not-use-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class User(BaseModel):
    username: str
    role: str  # "viewer" or "operator"


# Hardcoded users for the prototype.
# Passwords are hashed at import time so plaintext doesn't sit in memory.
_FAKE_USERS = {
    "viewer": {
        "username": "viewer",
        "role": "viewer",
        "password_hash": pwd_context.hash("viewer123"),
    },
    "operator": {
        "username": "operator",
        "role": "operator",
        "password_hash": pwd_context.hash("operator123"),
    },
}


def authenticate(username: str, password: str) -> Optional[User]:
    record = _FAKE_USERS.get(username)
    if not record:
        return None
    if not pwd_context.verify(password, record["password_hash"]):
        return None
    return User(username=record["username"], role=record["role"])


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user.username, "role": user.role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if not username or not role:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return User(username=username, role=role)


def require_operator(user: User = Depends(get_current_user)) -> User:
    """Dependency that rejects requests from non-operator users."""
    if user.role != "operator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role required for this action",
        )
    return user
