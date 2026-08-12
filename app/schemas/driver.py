"""
Driver schemas — CRUD operations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DriverCreate(BaseModel):
    carrier_id: UUID
    full_name: str
    phone: str | None = None
    license_number: str | None = None


class DriverUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    license_number: str | None = None
    is_active: bool | None = None


class DriverResponse(BaseModel):
    id: UUID
    carrier_id: UUID
    full_name: str
    phone: str | None = None
    license_number: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
