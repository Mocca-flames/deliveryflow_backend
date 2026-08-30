"""
Driver's Packs API routes — CRUD, review queue, admin clearance.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_current_user, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.drivers_pack import DriversPackCreate, DriversPackResponse
from app.services.drivers_pack import DriversPackService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[DriversPackResponse])
async def list_drivers_packs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List driver's packs for current tenant."""
    svc = DriversPackService(db)
    packs, total = await svc.list(tenant.id, page, per_page, status)
    pages = (total + per_page - 1) // per_page

    return PaginatedResponse(
        items=[DriversPackResponse.model_validate(p) for p in packs],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("/", response_model=DriversPackResponse, status_code=status.HTTP_201_CREATED)
async def create_drivers_pack(
    body: DriversPackCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new driver's pack."""
    svc = DriversPackService(db)
    pack = await svc.create(tenant.id, body.driver_id, body.vehicle_id)
    return DriversPackResponse.model_validate(pack)


@router.get("/queue", response_model=list[DriversPackResponse])
async def review_queue(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin review queue — flagged packs."""
    svc = DriversPackService(db)
    packs = await svc.review_queue(tenant.id)
    return [DriversPackResponse.model_validate(p) for p in packs]


@router.get("/{pack_id}", response_model=DriversPackResponse)
async def get_drivers_pack(
    pack_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a driver's pack by ID."""
    svc = DriversPackService(db)
    pack = await svc.get(pack_id, tenant.id)
    if pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver's pack not found")
    return DriversPackResponse.model_validate(pack)


@router.post("/{pack_id}/clear", response_model=DriversPackResponse)
async def clear_pack(
    pack_id: UUID,
    notes: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin manual clearance of a flagged pack."""
    svc = DriversPackService(db)
    pack = await svc.get(pack_id, tenant.id)
    if pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver's pack not found")

    if pack.status != "flagged":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only flagged packs can be cleared")

    try:
        pack = await svc.clear(pack, user.id, notes)
        return DriversPackResponse.model_validate(pack)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
