"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Role(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default=Role.VIEWER)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
