"""
Vehicle schemas — CRUD operations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class VehicleCreate(BaseModel):
    carrier_id: UUID
    registration: str
    make: str | None = None
    model: str | None = None
    year: int | None = None


class VehicleUpdate(BaseModel):
    make: str | None = None
    model: str | None = None
    year: int | None = None
    is_active: bool | None = None


class VehicleResponse(BaseModel):
    id: UUID
    carrier_id: UUID
    registration: str
    make: str | None = None
    model: str | None = None
    year: int | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
