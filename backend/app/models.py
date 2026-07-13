"""SQLAlchemy ORM models (fastapi-users compatible)."""

from __future__ import annotations

from enum import StrEnum

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Role(StrEnum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(SQLAlchemyBaseUserTableUUID, Base):
    """User model.

    Inherits from fastapi-users base: gives us id (UUID), email, hashed_password,
    is_active, is_superuser, is_verified. We add a `role` for viewer/operator/admin
    semantics on top of `is_superuser`.
    """

    role: Mapped[str] = mapped_column(String(16), default=Role.VIEWER.value)
