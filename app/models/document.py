import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Document(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id"), nullable=True
    )
    drivers_pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers_packs.id"), nullable=True
    )
    doc_type: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ocr_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ocr_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False
    )

    # Relationships
    trip = relationship("Trip", back_populates="documents")
