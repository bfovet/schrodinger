from collections.abc import Sequence
from typing import Any, Self
from sqlalchemy import Select, func, select
from sqlalchemy.orm.attributes import flag_modified
from schrodinger.kit.db.postgres import AsyncReadSession, AsyncSession


class RepositoryBase[M]:
    model: type[M]

    def __init__(self, session: AsyncSession | AsyncReadSession) -> None:
        self.session = session

    async def get_one_or_none(self, statement: Select[tuple[M]]) -> M | None:
        result = await self.session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def get_all(self, statement: Select[tuple[M]]) -> Sequence[M]:
        result = await self.session.execute(statement)
        return result.scalars().unique().all()

    def get_base_statement(self) -> Select[tuple[M]]:
        return select(self.model)

    async def create(self, object: M, *, flush: bool = False) -> M:
        self.session.add(object)

        if flush:
            await self.session.flush()

        return object

    async def update(
        self,
        object: M,
        *,
        update_dict: dict[str, Any] | None = None,
        flush: bool = False,
    ) -> M:
        if update_dict is not None:
            for attr, value in update_dict.items():
                setattr(object, attr, value)
                # Always consider that the attribute was modified if it's explictly set
                # in the update_dict. This forces SQLAlchemy to include it in the
                # UPDATE statement, even if the value is the same as before.
                # Ref: https://docs.sqlalchemy.org/en/20/orm/session_api.html#sqlalchemy.orm.attributes.flag_modified
                try:
                    flag_modified(object, attr)
                # Don't fail if the attribute is not tracked by SQLAlchemy
                except KeyError:
                    pass

        self.session.add(object)

        if flush:
            await self.session.flush()

        return object

    async def count(self, statement: Select[tuple[M]]) -> int:
        count_statement = statement.with_only_columns(func.count())
        result = await self.session.execute(count_statement)
        return result.scalar_one()

    @classmethod
    def from_session(cls, session: AsyncSession | AsyncReadSession) -> Self:
        return cls(session)
