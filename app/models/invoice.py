import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invoices"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id"), unique=True, nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")

    # Amounts
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String, default="ZAR")
    upfront_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("70.00"))
    balance_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("30.00"))
    upfront_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    balance_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # Milestone tracking
    current_milestone: Mapped[str] = mapped_column(String, default="none")

    # Dates
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    upfront_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    balance_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    trip = relationship("Trip", back_populates="invoice")
    milestones = relationship("InvoiceMilestone", back_populates="invoice", order_by="InvoiceMilestone.created_at")


class InvoiceMilestone(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "invoice_milestones"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )
    milestone: Mapped[str] = mapped_column(String, nullable=False)
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)
    to_status: Mapped[str] = mapped_column(String, nullable=False)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    trigger_source: Mapped[str] = mapped_column(String, default="manual")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    # Relationships
    invoice = relationship("Invoice", back_populates="milestones")
