"""
Documents API routes — upload, download, verification.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_user, get_current_tenant
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.document import DocumentResponse, DocumentVerify
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
