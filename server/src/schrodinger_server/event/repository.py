from collections.abc import Sequence
from uuid import UUID

from schrodinger_server.kit.repository.base import RepositoryBase, RepositoryIDMixin
from schrodinger_server.models.event import Event


class EventRepository(RepositoryBase[Event], RepositoryIDMixin[Event, UUID]):
    model = Event

    async def get_all_by_name(self, name: str) -> Sequence[Event]:
        statement = self.get_base_statement().where(Event.name == name)
        return await self.get_all(statement)
