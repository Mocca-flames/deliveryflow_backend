"""
Invoices API routes — CRUD, issue, verify PoD, PDF generation.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_current_user, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.invoice import InvoiceResponse, MilestoneResponse
from app.services.invoice import InvoiceService

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
        # Build data structure matching the invoice.html template
        # Get tenant info for company details
        tenant = invoice.trip.tenant if invoice.trip else None
        tenant_settings = tenant.settings if tenant else {}
        branding = tenant_settings.get("branding", {})
        
        # Get logo base64 if available
        logo_base64 = ""
        if branding.get("logo_storage_key"):
            from app.services.pdf_generator import pdf_generator
            logo_base64 = pdf_generator._get_base64_logo(branding["logo_storage_key"])

        data = {
            "document_title": "INVOICE",
            "document_number": invoice.invoice_number,
            "primary_color": branding.get("primary_color", "#2c5aa0"),
            "logo_base64": logo_base64,
            "company": {
                "name": tenant.name if tenant else "DeliveryFlow",
                "address": tenant_settings.get("address", "123 Freight Street"),
                "city": tenant_settings.get("city", "Johannesburg"),
                "postal_code": tenant_settings.get("postal_code", "2000"),
                "country": tenant_settings.get("country", "South Africa"),
                "phone": tenant_settings.get("phone", "+27 11 123 4567"),
                "email": tenant_settings.get("email", "billing@deliveryflow.co.za"),
                "website": tenant_settings.get("website"),
                "registration_number": tenant_settings.get("registration_number", "2024/123456/07"),
                "tax_number": tenant_settings.get("tax_number"),
            },
            "client": {
                "name": invoice.trip.client_name or "Client",
                "company": None,
                "address": invoice.trip.client_address or "Client Address",
                "city": invoice.trip.client_city or "City",
                "postal_code": invoice.trip.client_postal_code or "0000",
                "country": invoice.trip.client_country or "South Africa",
            },
            "invoice_number": invoice.invoice_number,
            "issue_date": invoice.issued_at.strftime("%d %B %Y") if invoice.issued_at else "N/A",
            "due_date": invoice.due_date.strftime("%d %B %Y") if invoice.due_date else "N/A",
            "trip_reference": invoice.trip.reference,
            "currency": invoice.currency,
            "origin": invoice.trip.origin,
            "destination": invoice.trip.destination,
            "status": invoice.status,
            "items": [
                {
                    "description": f"Freight - {invoice.trip.reference}",
                    "quantity": 1,
                    "unit_price": float(invoice.total_amount),
                    "amount": float(invoice.total_amount),
                }
            ],
            "subtotal": float(invoice.total_amount),
            "tax_amount": 0,
            "tax_pct": 0,
            "total": float(invoice.total_amount),
            "upfront_amount": float(invoice.total_amount) * (float(invoice.upfront_pct) / 100),
            "balance_amount": float(invoice.total_amount) * (float(invoice.balance_pct) / 100),
            "notes": invoice.notes or "",
            "invoice_footer": branding.get("invoice_footer"),
        }

        pdf_bytes = await pdf_generator.generate_invoice(data)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PDF generation failed: {e}")
