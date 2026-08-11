import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DriversPack(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "drivers_packs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")

    # State tracking
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Review
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Document references
    vehicle_licence_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    drivers_licence_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    id_document_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    insurance_letter_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )

    # OCR cross-check
    ocr_cross_check: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ocr_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Relationships
    driver = relationship("Driver", back_populates="drivers_packs")
    vehicle = relationship("Vehicle", back_populates="drivers_packs")
