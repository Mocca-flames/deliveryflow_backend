import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Trip(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "trips"
    __table_args__ = (UniqueConstraint("tenant_id", "reference", name="uq_trip_tenant_reference"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    reference: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")

    # Parties
    carrier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("carriers.id"), nullable=True
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True
    )

    # Route
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)

    # Client info
    client_name: Mapped[str | None] = mapped_column(String, nullable=True)
    client_email: Mapped[str | None] = mapped_column(String, nullable=True)
    client_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    client_address: Mapped[str | None] = mapped_column(String, nullable=True)
    client_city: Mapped[str | None] = mapped_column(String, nullable=True)
    client_postal_code: Mapped[str | None] = mapped_column(String, nullable=True)
    client_country: Mapped[str | None] = mapped_column(String, nullable=True)

    # Cargo
    cargo_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    cargo_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Quotation
    quoted_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String, default="ZAR")

    # Contract
    contract_url: Mapped[str | None] = mapped_column(String, nullable=True)
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Dates
    pickup_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Tokenized links
    tracking_token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    carrier_token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    # Metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="trips")
    carrier = relationship("Carrier")
    driver = relationship("Driver")
    vehicle = relationship("Vehicle")
    invoice = relationship("Invoice", back_populates="trip", uselist=False)
    documents = relationship("Document", back_populates="trip")
    doc_requirements = relationship("TripDocumentRequirement", back_populates="trip")
    sync_events = relationship("SyncEvent", back_populates="trip")
