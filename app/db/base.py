"""
app.db.base
~~~~~~~~~~~~
SQLAlchemy declarative base and common model mixin.

Every ORM model in the project should inherit from ``BaseModel``::

    from app.db.base import BaseModel

    class Video(BaseModel):
        __tablename__ = "videos"

        title: Mapped[str] = mapped_column(String(255))

This automatically provides ``id``, ``created_at``, and ``updated_at``
columns — no need to redeclare them in each model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    """Top-level SQLAlchemy declarative base.

    Used as the registry for metadata and type mappings.  Do **not**
    subclass this directly for application models — use ``BaseModel``
    instead so you get the common columns for free.
    """

    pass


class BaseModel(Base):
    """Abstract mixin that adds standard columns to every model.

    Columns
    -------
    id : UUID
        Primary key, server-generated UUID v4.
    created_at : datetime
        Row-creation timestamp (set by the database).
    updated_at : datetime
        Last-modification timestamp (updated automatically on each write).
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id!s}>"
