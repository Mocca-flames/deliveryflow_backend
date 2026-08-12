"""
Trips API routes — CRUD, assignment, lifecycle operations.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.trip import TripCreate, TripResponse, TripAssign
from app.schemas.common import PaginatedResponse
from app.services.trip import TripService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[TripResponse])
async def list_trips(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List trips for current tenant."""
    svc = TripService(db)
    trips, total = await svc.list(tenant.id, page, per_page, status)
    pages = (total + per_page - 1) // per_page

    return PaginatedResponse(
        items=[TripResponse.model_validate(t) for t in trips],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    body: TripCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new trip."""
    svc = TripService(db)
    trip = await svc.create(tenant.id, body)
    return TripResponse.model_validate(trip)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get trip by ID."""
    svc = TripService(db)
    trip = await svc.get(trip_id, tenant.id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return TripResponse.model_validate(trip)


@router.post("/{trip_id}/assign", response_model=TripResponse)
async def assign_trip(
    trip_id: UUID,
    body: TripAssign,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign carrier, driver, vehicle to trip."""
    svc = TripService(db)
    trip = await svc.get(trip_id, tenant.id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    try:
        trip = await svc.assign(trip, body)
        return TripResponse.model_validate(trip)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{trip_id}/award-contract")
async def award_contract(
    trip_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Award contract to carrier — triggers driver pack gate check."""
    svc = TripService(db)
    trip = await svc.get(trip_id, tenant.id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    try:
        trip = await svc.assign(trip, TripAssign(
            carrier_id=trip.carrier_id,
            driver_id=trip.driver_id,
            vehicle_id=trip.vehicle_id,
        ))
        return {"message": "Contract awarded", "trip_id": str(trip_id)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{trip_id}/begin-transit")
async def begin_transit(
    trip_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark trip as in transit."""
    svc = TripService(db)
    trip = await svc.get(trip_id, tenant.id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    trip = await svc.begin_transit(trip)
    return {"message": "Transit started", "trip_id": str(trip_id), "status": trip.status}


@router.post("/{trip_id}/complete")
async def complete_trip(
    trip_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark trip as completed."""
    svc = TripService(db)
    trip = await svc.get(trip_id, tenant.id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    trip = await svc.complete(trip)
    return {"message": "Trip completed", "trip_id": str(trip_id), "status": trip.status}


@router.post("/{trip_id}/cancel")
async def cancel_trip(
    trip_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a trip."""
    svc = TripService(db)
    trip = await svc.get(trip_id, tenant.id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    trip = await svc.cancel(trip)
    return {"message": "Trip cancelled", "trip_id": str(trip_id), "status": trip.status}


@router.get("/{trip_id}/doc-checklist")
async def get_doc_checklist(
    trip_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document checklist for a trip."""
    svc = TripService(db)
    checklist = await svc.get_doc_checklist(trip_id, tenant.id)
    return checklist
