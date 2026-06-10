"""
Async SQLAlchemy engine + session.

DB URL is controlled by the DATABASE_URL env var.
Defaults to SQLite at backend/data/users.db.
Swap to Postgres later by changing the URL only.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

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
