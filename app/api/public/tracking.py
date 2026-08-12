"""
Public tracking API routes — no auth required.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.services.tracking import TrackingService
from app.core.exceptions import TokenNotFoundError

router = APIRouter()


@router.get("/track/{token}")
async def get_tracking(token: str, db: AsyncSession = Depends(get_db)):
    """Public tracking link — no auth required."""
    svc = TrackingService(db)
    try:
        return await svc.get_tracking_data(token)
    except TokenNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/track/{token}/status")
async def get_tracking_status(token: str, db: AsyncSession = Depends(get_db)):
    """Polling endpoint for tracking updates."""
    svc = TrackingService(db)
    try:
        return await svc.get_tracking_status(token)
    except TokenNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
