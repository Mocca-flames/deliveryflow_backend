"""
Tenant schemas — CRUD operations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

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
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProvisionTenantRequest(BaseModel):
    """Platform-admin request to provision a new tenant + admin user."""

    email: EmailStr
    password: str
    full_name: str | None = None
    tenant_name: str | None = None
    slug: str | None = None
    business_type: BusinessType = BusinessType.LOGISTICS


class ProvisionTenantResponse(BaseModel):
    """Result of a tenant provisioning call, including a usable access token."""

    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    business_type: BusinessType
    user_id: UUID
    email: EmailStr
    role: str
    created: bool
    access_token: str
