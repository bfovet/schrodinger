from datetime import datetime
from typing import Annotated

from fastapi import Path
from pydantic import UUID4, Field

from schrodinger_server.detection.detection import CocoClassId
from schrodinger_server.kit.schemas import IDSchema, Schema


class BaseEvent(IDSchema):
    timestamp: datetime = Field(description="The timestamp of the event.")


class EntityDetectedEvent(BaseEvent):
    """An event created when an entity is detected."""

    entity_id: CocoClassId = Field(description="The ID of the entity.")
    name: str = Field(description="The name of the entity.")
    event_type: str = Field(description="The type of the event.")
    timestamp: datetime = Field(description="The timestamp of the event.")
    s3_key: str = Field(description="S3 link to the event frame")


type Event = EntityDetectedEvent


class EventName(Schema):
    name: str = Field(description="The name of the event.")
    first_seen: datetime = Field(description="The first time the event occurred.")
    last_seen: datetime = Field(description="The last time the event occurred.")


EventID = Annotated[UUID4, Path(description="The event ID.")]
