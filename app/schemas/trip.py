from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    reference: str
    origin: str
    destination: str
    client_name: str | None = None
    client_email: str | None = None
    client_phone: str | None = None
    client_address: str | None = None
    client_city: str | None = None
    client_postal_code: str | None = None
    client_country: str | None = None
    cargo_desc: str | None = None
    cargo_weight_kg: Decimal | None = None
    quoted_amount: Decimal | None = None
    currency: str = "ZAR"
    pickup_date: date | None = None
    delivery_date: date | None = None
    notes: str | None = None


class TripResponse(BaseModel):
    id: UUID
    reference: str
    status: str
    origin: str
    destination: str
    carrier_id: UUID | None = None
    driver_id: UUID | None = None
    vehicle_id: UUID | None = None
    client_name: str | None = None
    client_email: str | None = None
    client_phone: str | None = None
    client_address: str | None = None
    client_city: str | None = None
    client_postal_code: str | None = None
    client_country: str | None = None
    quoted_amount: Decimal | None = None
    currency: str = "ZAR"
    tracking_token: str | None = None
    carrier_token: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TripAssign(BaseModel):
    carrier_id: UUID
    driver_id: UUID
    vehicle_id: UUID
