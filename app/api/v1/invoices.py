from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_invoices():
    return {"message": "list invoices"}


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: str):
    return {"invoice_id": invoice_id}


@router.post("/{invoice_id}/issue")
async def issue_invoice(invoice_id: str):
    return {"invoice_id": invoice_id, "action": "issue"}


@router.post("/{invoice_id}/verify-pod")
async def verify_pod(invoice_id: str):
    """Human-verify PoD — unlocks 30% balance (HITL)."""
    return {"invoice_id": invoice_id, "action": "verify-pod"}
