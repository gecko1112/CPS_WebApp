"""
DB-backed auth with three roles: viewer, operator, admin.

Secret key + admin seed credentials are read from env vars (.env.example).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import Base, SessionLocal, engine, get_session
from .models import Role, User as UserModel

SECRET_KEY = os.getenv("JWT_SECRET", "dev-only-secret-do-not-use-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class User(BaseModel):
    """Public user shape (no password)."""

    username: str
    role: str


# ---------------------------------------------------------------------------
# Startup: create tables + seed admin
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """Create tables and seed an admin if one doesn't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_users()


async def _seed_users() -> None:
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pw = os.getenv("ADMIN_PASSWORD")
    seed_dev = os.getenv("SEED_DEV_USERS", "true").lower() in ("1", "true", "yes")

    async with SessionLocal() as session:
        if admin_user and admin_pw:
            await _create_if_missing(session, admin_user, admin_pw, Role.ADMIN)

        if seed_dev:
            await _create_if_missing(session, "viewer", "viewer123", Role.VIEWER)
            await _create_if_missing(session, "operator", "operator123", Role.OPERATOR)

        await session.commit()


async def _create_if_missing(
    session: AsyncSession, username: str, password: str, role: Role
) -> None:
    existing = await session.scalar(
        select(UserModel).where(UserModel.username == username)
    )
    if existing:
        return
    session.add(
        UserModel(
            username=username,
            password_hash=pwd_context.hash(password),
            role=role.value,
        )
    )


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
async def authenticate(
    session: AsyncSession, username: str, password: str
) -> User | None:
    record = await session.scalar(
        select(UserModel).where(UserModel.username == username)
    )
    if not record:
        return None
    if not pwd_context.verify(password, record.password_hash):
        return None
    record.last_login = datetime.now(timezone.utc)
    await session.commit()
    return User(username=record.username, role=record.role)


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
    if user.role not in (Role.OPERATOR.value, Role.ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role required for this action",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this action",
        )
    return user
