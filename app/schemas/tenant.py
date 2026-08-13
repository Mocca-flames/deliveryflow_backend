"""
Tenant schemas — CRUD operations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import BusinessType


class TenantCreate(BaseModel):
    name: str
    slug: str
    business_type: BusinessType = BusinessType.LOGISTICS


class TenantUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    business_type: BusinessType | None = None


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    business_type: BusinessType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
