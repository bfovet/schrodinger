from collections.abc import Sequence
from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime

from schrodinger.exceptions import ResourceNotFound
from schrodinger.kit.db.postgres import AsyncSession
from schrodinger.models.event import Event
from schrodinger.postgres import get_db_session
from schrodinger.event.schemas import Event as EventSchema, EventID
from schrodinger.event.service import event as event_service

router = APIRouter(prefix="/events", redirect_slashes=True, tags=["events"])


EventNotFound = {"description": "Event not found.", "model": ResourceNotFound.schema()}


@router.get("/", summary="List Events", response_model=list[EventSchema])
async def list(
    start_timestamp: AwareDatetime | None = Query(
        None, description="Filter events after this timestamp."
    ),
    end_timestamp: AwareDatetime | None = Query(
        None, description="Filter events before this timestamp."
    ),
    name: str | None = Query(
        None, title="Name Filter", description="Filter by event name."
    ),
    session: AsyncSession = Depends(get_db_session),
) -> Sequence[EventSchema]:
    """List events."""

    results, count = await event_service.list(session, start_timestamp=start_timestamp, end_timestamp=end_timestamp, name=name)

    return results


@router.post("/{id}", summary="Get Event", response_model=EventSchema, responses={404: EventNotFound})
async def get(id: EventID, session: AsyncSession = Depends(get_db_session)) -> Event:
    """
    Get an event by ID.
    """
    event = await event_service.get(session, id)

    if event is None:
        raise ResourceNotFound()
    
    return event
