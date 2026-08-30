"""
Public carrier portal API routes — tokenized access for carriers.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.trip import Trip
from app.services.document import DocumentService

router = APIRouter()


async def _get_trip_by_carrier_token(db: AsyncSession, token: str) -> Trip:
    """Internal: get trip by carrier token."""
    stmt = select(Trip).where(Trip.carrier_token == token)
    result = await db.execute(stmt)
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=404, detail="Invalid carrier portal link")
    return trip


@router.get("/carrier/{token}")
async def get_carrier_portal(token: str, db: AsyncSession = Depends(get_db)):
    """Carrier portal — trip details, action forms."""
    trip = await _get_trip_by_carrier_token(db, token)
    return {
        "trip_id": str(trip.id),
        "reference": trip.reference,
        "status": trip.status,
        "origin": trip.origin,
        "destination": trip.destination,
        "cargo_desc": trip.cargo_desc,
        "pickup_date": str(trip.pickup_date) if trip.pickup_date else None,
        "delivery_date": str(trip.delivery_date) if trip.delivery_date else None,
    }


@router.post("/carrier/{token}/accept")
async def carrier_accept(token: str, db: AsyncSession = Depends(get_db)):
    """Carrier accepts trip."""
    trip = await _get_trip_by_carrier_token(db, token)

    if trip.status != "draft":
        raise HTTPException(status_code=400, detail="Trip cannot be accepted in current status")

    trip.status = "assigned"
    await db.flush()
    await db.commit()

    return {"message": "Trip accepted", "trip_id": str(trip.id), "status": trip.status}


@router.post("/carrier/{token}/pod")
async def carrier_upload_pod(
    token: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Carrier uploads PoD."""
    trip = await _get_trip_by_carrier_token(db, token)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    svc = DocumentService(db)
    try:
        doc = await svc.upload(
            tenant_id=trip.tenant_id,
            file_content=content,
            filename=file.filename or "pod",
            mime_type=file.content_type or "application/octet-stream",
            doc_type="pod_photo",
            trip_id=trip.id,
        )
        return {"message": "PoD uploaded", "document_id": str(doc.id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/carrier/{token}/border-docs")
async def carrier_upload_border_docs(
    token: str,
    file: UploadFile = File(...),
    doc_type: str = "cross_border_permit",
    db: AsyncSession = Depends(get_db),
):
    """Carrier uploads border clearance docs."""
    trip = await _get_trip_by_carrier_token(db, token)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    svc = DocumentService(db)
    try:
        doc = await svc.upload(
            tenant_id=trip.tenant_id,
            file_content=content,
            filename=file.filename or doc_type,
            mime_type=file.content_type or "application/octet-stream",
            doc_type=doc_type,
            trip_id=trip.id,
        )
        return {"message": "Border docs uploaded", "document_id": str(doc.id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
