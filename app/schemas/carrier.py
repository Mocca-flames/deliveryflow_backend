"""
Carrier schemas — CRUD operations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CarrierCreate(BaseModel):
    name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class CarrierUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    is_active: bool | None = None


class CarrierResponse(BaseModel):
    id: UUID
    name: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
