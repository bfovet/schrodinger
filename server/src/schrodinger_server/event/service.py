import uuid
from collections.abc import Sequence
from datetime import datetime

from schrodinger_server.event.repository import EventRepository
from schrodinger_server.kit.db.postgres import AsyncSession
from schrodinger_server.models.event import Event


class EventService:
    async def list(
        self,
        session: AsyncSession,
        *,
        start_timestamp: datetime | None = None,
        end_timestamp: datetime | None = None,
        name: Sequence[str] | None = None,
    ) -> tuple[Sequence[Event], int]:
        repository = EventRepository.from_session(session)
        statement = repository.get_base_statement()

        if start_timestamp is not None:
            statement = statement.where(Event.timestamp > start_timestamp)

        if end_timestamp is not None:
            statement = statement.where(Event.timestamp < end_timestamp)

        if name is not None:
            statement = statement.where(Event.name.in_(name))

        # return await repository.paginate(statement, limit=pagination.limit, page=pagination.page)
        return await repository.get_all(statement), 0

    async def get(self, session: AsyncSession, id: uuid.UUID) -> Event | None:
        repository = EventRepository.from_session(session)
        statement = repository.get_base_statement().where(Event.id == id)
        return await repository.get_one_or_none(statement)

    async def create(self, session: AsyncSession, event: Event) -> Event:
        repository = EventRepository.from_session(session)
        event = await repository.create(event, flush=True)

        # TODO: log.debug("Event created")

        return event


event = EventService()
