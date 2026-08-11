from fastapi import APIRouter

router = APIRouter()


@router.get("/carrier/{token}")
async def get_carrier_portal(token: str):
    """Carrier portal — trip details, action forms."""
    return {"token": token, "trip": None}


@router.post("/carrier/{token}/accept")
async def carrier_accept(token: str):
    """Carrier accepts trip."""
    return {"token": token, "action": "accept"}


@router.post("/carrier/{token}/pod")
async def carrier_upload_pod(token: str):
    """Carrier uploads PoD."""
    return {"token": token, "action": "pod"}


@router.post("/carrier/{token}/border-docs")
async def carrier_upload_border_docs(token: str):
    """Carrier uploads border clearance docs."""
    return {"token": token, "action": "border-docs"}
