"""Generic async repository helpers."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.db.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class AsyncRepository(Generic[ModelType]):
    """Base CRUD repository for SQLAlchemy async models.

    Repositories flush and refresh instances so generated values are available,
    but they do not commit. Transaction boundaries stay with the caller or the
    FastAPI ``get_db`` dependency.
    """

    def __init__(self, session: AsyncSession, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    async def get(self, model_id: uuid.UUID) -> ModelType | None:
        """Return one row by primary key."""
        return await self.session.get(self.model, model_id)

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        filters: Sequence[ColumnElement[bool]] = (),
        order_by: ColumnElement[Any] | None = None,
    ) -> list[ModelType]:
        """Return a filtered page of rows."""
        statement = select(self.model)
        for criterion in filters:
            statement = statement.where(criterion)
        if order_by is not None:
            statement = statement.order_by(order_by)
        statement = statement.offset(offset).limit(limit)

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count(
        self,
        *,
        filters: Sequence[ColumnElement[bool]] = (),
    ) -> int:
        """Count rows matching optional filters."""
        statement = select(func.count()).select_from(self.model)
        for criterion in filters:
            statement = statement.where(criterion)

        result = await self.session.scalar(statement)
        return int(result or 0)

    async def exists(self, model_id: uuid.UUID) -> bool:
        """Return whether a primary key exists."""
        return await self.get(model_id) is not None

    async def create(
        self,
        data: Mapping[str, Any] | None = None,
        **values: Any,
    ) -> ModelType:
        """Create and flush a new row."""
        payload = dict(data or {})
        payload.update(values)

        instance = self.model(**payload)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(
        self,
        instance: ModelType,
        data: Mapping[str, Any] | None = None,
        **values: Any,
    ) -> ModelType:
        """Update and flush an existing row."""
        payload = dict(data or {})
        payload.update(values)

        for field, value in payload.items():
            setattr(instance, field, value)

        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update_by_id(
        self,
        model_id: uuid.UUID,
        data: Mapping[str, Any] | None = None,
        **values: Any,
    ) -> ModelType | None:
        """Update a row by primary key, returning ``None`` if missing."""
        instance = await self.get(model_id)
        if instance is None:
            return None
        return await self.update(instance, data, **values)

    async def delete(self, model_id: uuid.UUID) -> bool:
        """Delete a row by primary key."""
        instance = await self.get(model_id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True
