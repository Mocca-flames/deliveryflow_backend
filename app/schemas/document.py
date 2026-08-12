from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class DocumentUpload(BaseModel):
    trip_id: UUID | None = None
    drivers_pack_id: UUID | None = None
    doc_type: str
    filename: str


class DocumentResponse(BaseModel):
    id: UUID
    trip_id: UUID | None = None
    drivers_pack_id: UUID | None = None
    doc_type: str
    filename: str
    storage_key: str
    mime_type: str | None = None
    size_bytes: int | None = None
    ocr_result: dict | None = None
    ocr_confidence: Decimal | None = None
    uploaded_via: str = "web"
    verified: bool = False
    verified_at: datetime | None = None
    verification_notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentVerify(BaseModel):
    verified: bool
    notes: str | None = None


class TripDocRequirementResponse(BaseModel):
    id: UUID
    trip_id: UUID
    doc_type: str
    required: bool
    uploaded: bool
    document_id: UUID | None = None
    required_by: str | None = None
    category: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TripDocChecklistResponse(BaseModel):
    trip_id: UUID
    total_required: int
    uploaded: int
    missing: list[str]  # doc_types that are required but not uploaded
    is_complete: bool
    requirements: list[TripDocRequirementResponse]
