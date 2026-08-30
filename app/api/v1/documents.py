"""
Documents API routes — upload, download, verification, PDF generation.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_current_user, get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentVerify
from app.schemas.sadc_document import SadcDocumentRequest
from app.services.document import DocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    trip_id: UUID | None = Form(None),
    drivers_pack_id: UUID | None = Form(None),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    svc = DocumentService(db)
    try:
        doc = await svc.upload(
            tenant_id=tenant.id,
            file_content=content,
            filename=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
            doc_type=doc_type,
            trip_id=trip_id,
            drivers_pack_id=drivers_pack_id,
            uploaded_by=user.id,
        )
        return DocumentResponse.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a document."""
    svc = DocumentService(db)
    try:
        doc, content = await svc.download(doc_id, tenant.id)
        return Response(
            content=content,
            media_type=doc.mime_type or "application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={doc.filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document metadata."""
    svc = DocumentService(db)
    try:
        doc = await svc.get(doc_id, tenant.id)
        return DocumentResponse.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{doc_id}/verify", response_model=DocumentResponse)
async def verify_document(
    doc_id: UUID,
    body: DocumentVerify,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify or unverify a document (HITL)."""
    svc = DocumentService(db)
    try:
        doc = await svc.verify(
            doc_id=doc_id,
            tenant_id=tenant.id,
            verified=body.verified,
            verified_by=user.id,
            notes=body.notes,
        )
        return DocumentResponse.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/generate-pdf")
async def generate_sadc_pdf(
    body: SadcDocumentRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
):
    """Generate a SADC-compliant document PDF from structured data.
    
    Accepts a full SadcDocument with TemplateConfig and returns PDF bytes.
    Supports Classic Letterhead and Modern Compact templates.
    """
    from app.services.pdf_generator import pdf_generator

    # Map template ID to template file
    template_map = {
        "classic": "sadc_invoice_classic.html",
        "modern": "sadc_invoice_modern.html",
    }
    template_name = template_map.get(body.templateId, "sadc_invoice_classic.html")

    # Check if issuer has VAT items to determine has_vat flag
    has_vat = any(
        item.vatPercent is not None and item.vatPercent > 0
        for item in body.lineItems
    )

    # Build template data
    data = {
        "meta": body.meta.model_dump(),
        "issuer": body.issuer.model_dump(),
        "recipient": body.recipient.model_dump(),
        "lineItems": [item.model_dump() for item in body.lineItems],
        "totals": body.totals.model_dump(),
        "banking": body.banking.model_dump() if body.banking else None,
        "footer": body.footer.model_dump() if body.footer else None,
        "config": body.templateConfig.model_dump(),
        "has_vat_items": has_vat,
    }

    try:
        pdf_bytes = await pdf_generator.generate_sadc_document(data, template_name)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{body.meta.documentNumber}.pdf"'
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {e}",
        )
