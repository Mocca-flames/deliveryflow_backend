from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class InvoiceResponse(BaseModel):
    id: UUID
    trip_id: UUID
    invoice_number: str
    status: str
    total_amount: Decimal
    currency: str = "ZAR"
    upfront_pct: Decimal
    balance_pct: Decimal
    upfront_amount: Decimal | None = None
    balance_amount: Decimal | None = None
    current_milestone: str
    issued_at: datetime | None = None
    due_date: datetime | None = None
    upfront_paid_at: datetime | None = None
    balance_paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MilestoneResponse(BaseModel):
    id: UUID
    milestone: str
    from_status: str | None = None
    to_status: str
    trigger_source: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
