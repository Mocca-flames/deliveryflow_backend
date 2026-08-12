"""
Invoices API routes — CRUD, issue, verify PoD, PDF generation.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.invoice import InvoiceResponse, MilestoneResponse
from app.schemas.common import PaginatedResponse
from app.services.invoice import InvoiceService
from app.services.pdf_generator import pdf_generator

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[InvoiceResponse])
async def list_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for current tenant."""
    svc = InvoiceService(db)
    invoices, total = await svc.list(tenant.id, page, per_page, status)
    pages = (total + per_page - 1) // per_page

    return PaginatedResponse(
        items=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get invoice by ID."""
    svc = InvoiceService(db)
    invoice = await svc.get(invoice_id, tenant.id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return InvoiceResponse.model_validate(invoice)


@router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice(
    invoice_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue invoice — calculates 70/30 split."""
    svc = InvoiceService(db)
    invoice = await svc.get(invoice_id, tenant.id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    if invoice.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already issued")

    try:
        invoice = await svc.issue(invoice, user.id)
        return InvoiceResponse.model_validate(invoice)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{invoice_id}/verify-pod", response_model=InvoiceResponse)
async def verify_pod(
    invoice_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """HITL verify PoD — triggers balance release."""
    svc = InvoiceService(db)
    invoice = await svc.get(invoice_id, tenant.id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    try:
        invoice = await svc.verify_pod(invoice, user.id)
        return InvoiceResponse.model_validate(invoice)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{invoice_id}/milestones", response_model=list[MilestoneResponse])
async def get_milestones(
    invoice_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get milestone history for an invoice."""
    svc = InvoiceService(db)
    milestones = await svc.get_milestones(invoice_id, tenant.id)
    return [MilestoneResponse.model_validate(m) for m in milestones]


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download invoice as PDF."""
    svc = InvoiceService(db)
    invoice = await svc.get(invoice_id, tenant.id)
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    try:
        pdf_bytes = await pdf_generator.generate_invoice(
            invoice_number=invoice.invoice_number,
            issued_date=invoice.issued_at.strftime("%d %B %Y") if invoice.issued_at else "N/A",
            due_date="",
            from_party={"name": "DeliveryFlow", "address": "", "reg": ""},
            to_party={"name": "", "address": "", "reg": ""},
            route={"origin": invoice.trip.origin, "destination": invoice.trip.destination},
            line_items=[{"description": f"Freight - {invoice.trip.reference}", "qty": 1, "unit_price": invoice.total_amount, "total": invoice.total_amount}],
            subtotal=invoice.total_amount,
            tax=0,
            grand_total=invoice.total_amount,
            payment_terms=f"{invoice.upfront_pct}% upfront, {invoice.balance_pct}% on completion",
            notes=invoice.notes or "",
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PDF generation failed: {e}")
