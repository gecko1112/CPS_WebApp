"""
Async SQLAlchemy engine + session + fastapi-users DB adapter.

DB URL is controlled by the DATABASE_URL env var.
Defaults to SQLite at backend/data/users.db.
Swap to Postgres later by changing the URL only.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from schema.utils import package_root, workspace_root
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Load the root .env into the process environment before anything reads env
# vars. db.py is the first app module imported, so doing it here covers
# auth.py and the rest of the app startup path too. Harmless no-op if the
# process already has these vars from a sourced root .env upstream —
# load_dotenv doesn't override already-set vars. This also keeps standalone
# backend runs (`cd backend && uv run uvicorn ...`, outside mprocs) working.
_BACKEND_ROOT = package_root(__file__)
load_dotenv(workspace_root(__file__) / ".env")
# Solo-repo standalone runs keep their config in backend/.env (the monorepo
# has no such file, so this is a no-op there). load_dotenv never overrides
# already-set vars, so the workspace root .env wins when both exist.
load_dotenv(_BACKEND_ROOT / ".env")

_DEFAULT_DB_PATH = _BACKEND_ROOT / "data" / "users.db"
_DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}")


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        yield session


# Imported lazily to avoid circular import (models -> db -> models)
if TYPE_CHECKING:
    pass


async def get_user_db(session: AsyncSession = Depends(get_session)):
    from .models import User

    yield SQLAlchemyUserDatabase(session, User)
