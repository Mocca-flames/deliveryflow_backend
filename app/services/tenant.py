"""
Tenant provisioning service.

Creates a Tenant together with its first `tenant_admin` user in a single
transaction. Used by both the platform-admin API endpoint and the CLI so the
logic is never duplicated.

The operation is idempotent: if a user with the given email already exists,
no new records are created and the existing credentials are returned.
"""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.enums import BusinessType
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import create_access_token

SLUG_INVALID = re.compile(r"[^a-z0-9]+")


@dataclass
class TenantProvisioningResult:
    tenant: Tenant
    user: User
    created: bool
    password: str | None
    access_token: str


async def provision_tenant(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    tenant_name: str | None = None,
    slug: str | None = None,
    business_type: BusinessType = BusinessType.LOGISTICS,
    role: str = "tenant_admin",
    email_verified: bool = True,
) -> TenantProvisioningResult:
    """Create a tenant + admin user, or return the existing user if the email is taken."""
    existing = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        tenant = None
        if existing.tenant_id is not None:
            tenant = (
                await db.execute(select(Tenant).where(Tenant.id == existing.tenant_id))
            ).scalar_one_or_none()
        else:
            # Orphaned user (e.g. registered via /auth/register) — give them a tenant.
            local = existing.email.split("@")[0]
            name = existing.full_name or local.title()
            base = SLUG_INVALID.sub("-", local.lower()).strip("-") or "tenant"
            slug = base
            n = 1
            while (
                await db.execute(select(Tenant).where(Tenant.slug == slug))
            ).scalar_one_or_none():
                slug = f"{base}-{n}"
                n += 1
            tenant = Tenant(
                name=name,
                slug=slug,
                business_type=BusinessType.LOGISTICS,
                is_active=True,
                settings={},
            )
            db.add(tenant)
            await db.flush()
            existing.tenant_id = tenant.id
            await db.commit()
            await db.refresh(existing)

        token = create_access_token(existing.id, existing.tenant_id)
        return TenantProvisioningResult(
            tenant=tenant,
            user=existing,
            created=False,
            password=None,
            access_token=token,
        )

    local = email.split("@")[0]
    full_name = full_name or local.title()
    tenant_name = tenant_name or full_name

    if not slug:
        base = SLUG_INVALID.sub("-", local.lower()).strip("-") or "tenant"
        slug = base
        n = 1
        while (await db.execute(select(Tenant).where(Tenant.slug == slug))).scalar_one_or_none():
            slug = f"{base}-{n}"
            n += 1

    tenant = Tenant(
        name=tenant_name,
        slug=slug,
        business_type=business_type,
        is_active=True,
        settings={},
    )
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
        is_email_verified=email_verified,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.tenant_id)
    return TenantProvisioningResult(
        tenant=tenant,
        user=user,
        created=True,
        password=password,
        access_token=token,
    )


@dataclass
class SuperAdminResult:
    user: User
    created: bool
    password: str | None
    access_token: str


async def ensure_superadmin(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
) -> SuperAdminResult:
    """Ensure a `super_admin` user exists with the given credentials.

    Idempotent: re-running updates role/password on an existing account
    rather than failing. Existing tenant-admins are promoted in place.
    """
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()

    if user is None:
        user = User(
            tenant_id=None,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name or email.split("@")[0].title(),
            role="super_admin",
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        created = True
        set_pw = password
    else:
        user.role = "super_admin"
        user.is_active = True
        user.is_email_verified = True
        # Refresh the password so the provided seed credentials always work.
        user.password_hash = hash_password(password)
        created = False
        set_pw = password
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user.id, user.tenant_id)
    return SuperAdminResult(user=user, created=created, password=set_pw, access_token=token)
