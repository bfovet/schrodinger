from datetime import datetime
from pydantic import Field
from schrodinger.detection.detection import CocoClassId
from schrodinger.kit.schemas import IDSchema


class EventBase(IDSchema):
    timestamp: datetime = Field(description="The timestamp of the event.")


class EntityDetectedEvent(EventBase):
    """An event created when an entity is detected."""

    entity_id: CocoClassId = Field(description="The ID of the entity.")
    start_time: datetime = Field(description="The start time of the event.")
    end_time: datetime = Field(description="The end time of the event.")


class EntityDetectedEventCreate(EventBase):
    pass
