"""
Document service — file upload, storage, retrieval, verification.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, TripDocumentRequirement
from app.storage.seaweed import SeaweedStorage
from app.core.exceptions import DeliveryFlowError
from app.config import get_settings

settings = get_settings()

# Lazy-init storage
_storage: SeaweedStorage | None = None


def _get_storage() -> SeaweedStorage:
    global _storage
    if _storage is None:
        _storage = SeaweedStorage()
    return _storage


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload(
        self,
        tenant_id: UUID,
        file_content: bytes,
        filename: str,
        mime_type: str,
        doc_type: str,
        trip_id: UUID | None = None,
        drivers_pack_id: UUID | None = None,
        uploaded_by: UUID | None = None,
    ) -> Document:
        """Upload document to storage and create DB record."""
        now = datetime.now(timezone.utc)
        storage = _get_storage()

        # Generate unique storage key
        storage_key = f"{tenant_id}/{doc_type}/{now.strftime('%Y%m%d_%H%M%S')}_{filename}"

        # Upload to SeaweedFS
        try:
            await storage.put(storage_key, file_content, mime_type)
        except Exception as e:
            raise DeliveryFlowError(f"Storage upload failed: {e}")

        # Create DB record
        doc = Document(
            tenant_id=tenant_id,
            trip_id=trip_id,
            drivers_pack_id=drivers_pack_id,
            doc_type=doc_type,
            filename=filename,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=len(file_content),
            uploaded_by=uploaded_by,
            uploaded_via="api",
            created_at=now,
        )
        self.db.add(doc)
        await self.db.flush()

        # Update trip document requirement if applicable
        if trip_id:
            await self._update_requirement(tenant_id, trip_id, doc_type, doc.id)

        return doc

    async def download(self, doc_id: UUID, tenant_id: UUID) -> tuple[Document, bytes]:
        """Download document from storage."""
        doc = await self._get_doc(doc_id, tenant_id)
        storage = _get_storage()

        try:
            content = await storage.get(doc.storage_key)
        except Exception as e:
            raise DeliveryFlowError(f"Storage download failed: {e}")

        return doc, content

    async def get(self, doc_id: UUID, tenant_id: UUID) -> Document:
        """Get document by ID."""
        return await self._get_doc(doc_id, tenant_id)

    async def verify(
        self,
        doc_id: UUID,
        tenant_id: UUID,
        verified: bool,
        verified_by: UUID,
        notes: str | None = None,
    ) -> Document:
        """Verify/unverify a document."""
        doc = await self._get_doc(doc_id, tenant_id)
        doc.verified = verified
        doc.verified_by = verified_by
        doc.verified_at = datetime.now(timezone.utc)
        doc.verification_notes = notes
        await self.db.flush()
        return doc

    async def list_by_trip(self, trip_id: UUID, tenant_id: UUID) -> list[Document]:
        """List all documents for a trip."""
        stmt = select(Document).where(
            Document.trip_id == trip_id,
            Document.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_doc(self, doc_id: UUID, tenant_id: UUID) -> Document:
        """Internal: get document or raise."""
        stmt = select(Document).where(
            Document.id == doc_id,
            Document.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()
        if doc is None:
            raise DeliveryFlowError("Document not found")
        return doc

    async def _update_requirement(
        self,
        tenant_id: UUID,
        trip_id: UUID,
        doc_type: str,
        document_id: UUID,
    ) -> None:
        """Update trip document requirement after upload."""
        stmt = select(TripDocumentRequirement).where(
            TripDocumentRequirement.trip_id == trip_id,
            TripDocumentRequirement.tenant_id == tenant_id,
            TripDocumentRequirement.doc_type == doc_type,
        )
        result = await self.db.execute(stmt)
        req = result.scalar_one_or_none()

        if req:
            req.uploaded = True
            req.document_id = document_id
            req.updated_at = datetime.now(timezone.utc)
