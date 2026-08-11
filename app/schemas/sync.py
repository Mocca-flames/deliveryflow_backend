from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SyncEventCreate(BaseModel):
    event_uuid: UUID
    device_id: str
    event_type: str
    payload: dict


class SyncEventBatch(BaseModel):
    events: list[SyncEventCreate]


class SyncEventResponse(BaseModel):
    id: UUID
    event_uuid: UUID
    device_id: str
    event_type: str
    processed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
