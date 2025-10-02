class EventRepository:
    def __init__(self, session: AsyncSession | AsyncReadSession) -> None:
        self.session = session