"""
fastapi-users wiring: user manager, JWT auth backend, role guards, admin seeding.

Auth URLs (mounted in main.py):
  POST /api/auth/jwt/login   → form-encoded email + password → {access_token, token_type}
  POST /api/auth/jwt/logout  → revoke (stateless JWT = no-op)
  POST /api/auth/register    → self-service signup (creates viewer)
  GET  /api/users/me         → current user details (includes role)
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.password import PasswordHelper
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy import select

from .db import Base, SessionLocal, engine, get_user_db
from .models import Role, User

SECRET = os.getenv("JWT_SECRET", "dev-only-secret-do-not-use-in-production")
TOKEN_LIFETIME_SECONDS = 60 * 60 * 24  # 1 day


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User registered: {user.email} (role={user.role})")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="api/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=TOKEN_LIFETIME_SECONDS)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------
def require_operator(user: User = Depends(current_active_user)) -> User:
    if user.role not in (Role.OPERATOR.value, Role.ADMIN.value) and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role required for this action",
        )
    return user


def require_admin(user: User = Depends(current_active_user)) -> User:
    if user.role != Role.ADMIN.value and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this action",
        )
    return user


# ---------------------------------------------------------------------------
# Startup: create tables + seed admin / dev users
# ---------------------------------------------------------------------------
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_users()


_password_helper = PasswordHelper()


async def _seed_users() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_pw = os.getenv("ADMIN_PASSWORD")
    seed_dev = os.getenv("SEED_DEV_USERS", "true").lower() in ("1", "true", "yes")

    async with SessionLocal() as session:
        if admin_email and admin_pw:
            await _create_if_missing(
                session, admin_email, admin_pw, Role.ADMIN, is_superuser=True
            )
        if seed_dev:
            await _create_if_missing(
                session, "viewer@example.com", "viewer123", Role.VIEWER
            )
            await _create_if_missing(
                session, "operator@example.com", "operator123", Role.OPERATOR
            )
        await session.commit()


async def _create_if_missing(
    session,
    email: str,
    password: str,
    role: Role,
    is_superuser: bool = False,
) -> None:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        return
    session.add(
        User(
            email=email,
            hashed_password=_password_helper.hash(password),
            is_active=True,
            is_verified=True,
            is_superuser=is_superuser,
            role=role.value,
        )
    )
