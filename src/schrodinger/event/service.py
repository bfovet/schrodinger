from schrodinger.models.event import EntityDetectedEvent


class EventService:
    async def create(self, session: AsyncSession, create_schema: EntityDetectedEventCreate) -> EntityDetectedEvent:
        repository = EventRepository.from_session(session)

        event = await repository.create(EntityDetectedEvent(), flush=True)
        await session.flush()

        return event
