from fastapi import APIRouter

router = APIRouter()


@router.get("/track/{token}")
async def get_tracking(token: str):
    """Public tracking link — no auth required."""
    return {
        "token": token,
        "milestones": [],
        "documents": [],
        "tracking": None,
    }


@router.get("/track/{token}/status")
async def get_tracking_status(token: str):
    """
    Polling endpoint for tracking updates.
    Client auto-refreshes every 15-30s. Returns latest status only.
    Response includes last_updated to skip re-render if unchanged.
    """
    return {
        "token": token,
        "status": None,
        "milestone": None,
        "last_updated": None,
    }
