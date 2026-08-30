"""
Platform (super-admin) API routes — tenant provisioning and oversight.

These endpoints are guarded by `require_super_admin`. They provide the
repeatable, API-driven path to onboard new logistics tenants, complementing
the CLI provisioning script.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_super_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import (
    ProvisionTenantRequest,
    ProvisionTenantResponse,
    TenantResponse,
)
from app.services.tenant import provision_tenant

router = APIRouter()


@router.post(
    "/tenants",
    response_model=ProvisionTenantResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["platform-admin"],
)
async def provision_tenant_endpoint(
    body: ProvisionTenantRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    """Create a new tenant and its first `tenant_admin` user."""
    result = await provision_tenant(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        tenant_name=body.tenant_name,
        slug=body.slug,
        business_type=body.business_type,
    )
    return ProvisionTenantResponse(
        tenant_id=result.tenant.id,
        tenant_name=result.tenant.name,
        tenant_slug=result.tenant.slug,
        business_type=result.tenant.business_type,
        user_id=result.user.id,
        email=result.user.email,
        role=result.user.role,
        created=result.created,
        access_token=result.access_token,
    )


@router.get(
    "/tenants",
    response_model=list[TenantResponse],
    tags=["platform-admin"],
)
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    """List all tenants."""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(result.scalars().all())
