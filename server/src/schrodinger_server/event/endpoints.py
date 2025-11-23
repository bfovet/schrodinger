from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query

from schrodinger_server.event.schemas import Event as EventSchema
from schrodinger_server.event.schemas import EventID
from schrodinger_server.event.service import event as event_service
from schrodinger_server.exceptions import ResourceNotFound
from schrodinger_server.kit.db.postgres import AsyncSession
from schrodinger_server.models.event import Event
from schrodinger_server.postgres import get_db_session

router = APIRouter(prefix="/events", redirect_slashes=True, tags=["events"])


EventNotFound = {"description": "Event not found.", "model": ResourceNotFound.schema()}


@router.get("/", summary="List Events", response_model=list[EventSchema])
async def list(
    name: str | None = Query(
        None, title="Name Filter", description="Filter by event name."
    ),
    session: AsyncSession = Depends(get_db_session),
) -> Sequence[EventSchema]:
    """List events."""

    results, count = await event_service.list(session, name=name)

    return results


@router.post(
    "/{id}",
    summary="Get Event",
    response_model=EventSchema,
    responses={404: EventNotFound},
)
async def get(id: EventID, session: AsyncSession = Depends(get_db_session)) -> Event:
    """
    Get an event by ID.
    """
    event = await event_service.get(session, id)

    if event is None:
        raise ResourceNotFound()

    return event
