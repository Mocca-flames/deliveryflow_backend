import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Carrier(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "carriers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="carriers")
    drivers = relationship("Driver", back_populates="carrier")
    vehicles = relationship("Vehicle", back_populates="carrier")
