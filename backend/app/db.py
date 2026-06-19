"""
Async SQLAlchemy engine + session + fastapi-users DB adapter.

DB URL is controlled by the DATABASE_URL env var.
Defaults to SQLite at backend/data/users.db.
Swap to Postgres later by changing the URL only.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Load backend/.env into the process environment before anything reads env vars.
# db.py is the first app module imported, so doing it here covers auth.py too.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users.db"
_DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH}"
)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        yield session


# Imported lazily to avoid circular import (models -> db -> models)
if TYPE_CHECKING:
    from .models import User


async def get_user_db(session: AsyncSession = Depends(get_session)):
    from .models import User
    yield SQLAlchemyUserDatabase(session, User)
