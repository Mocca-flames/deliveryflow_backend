from fastapi import APIRouter

router = APIRouter()


@router.post("/events")
async def sync_events():
    """Batch upload sync events from Flutter outbox."""
    return {"message": "sync events"}


@router.get("/events")
async def poll_events():
    """Poll for unprocessed events."""
    return {"message": "poll events"}
