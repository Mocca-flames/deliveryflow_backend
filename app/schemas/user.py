"""
User schemas — CRUD operations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "tenant_staff"
    tenant_id: UUID | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    tenant_id: UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
