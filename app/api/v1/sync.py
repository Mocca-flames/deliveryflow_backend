"""
Sync API routes — batch upload and poll events from Flutter outbox.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_current_user, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.sync import SyncService

router = APIRouter()


class SyncEventBatch(BaseModel):
    events: list[dict]


@router.post("/events")
async def sync_events(
    body: SyncEventBatch,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch upload sync events from Flutter outbox."""
    svc = SyncService(db)
    try:
        processed = await svc.process_batch(tenant.id, body.events)
        return {
            "message": f"Processed {len(processed)} events",
            "count": len(processed),
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/events")
async def poll_events(
    limit: int = Query(100, ge=1, le=500),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll for unprocessed events."""
    svc = SyncService(db)
    events = await svc.poll_unprocessed(tenant.id, limit)

    return {
        "events": [
            {
                "id": str(e.id),
                "trip_id": str(e.trip_id),
                "event_uuid": str(e.event_uuid),
                "device_id": e.device_id,
                "event_type": e.event_type,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "count": len(events),
    }
