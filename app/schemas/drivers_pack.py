from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DriversPackCreate(BaseModel):
    driver_id: UUID | None = None
    vehicle_id: UUID | None = None


class DriversPackResponse(BaseModel):
    id: UUID
    driver_id: UUID | None = None
    vehicle_id: UUID | None = None
    status: str
    submitted_at: datetime | None = None
    verified_at: datetime | None = None
    flagged_at: datetime | None = None
    cleared_at: datetime | None = None
    expires_at: datetime | None = None
    ocr_pass: bool | None = None
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
