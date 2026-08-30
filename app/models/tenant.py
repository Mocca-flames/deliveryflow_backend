from sqlalchemy import Boolean, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BusinessType


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(
        Enum(BusinessType, name="tenant_business_type", native_enum=False),
        nullable=False,
        server_default=BusinessType.LOGISTICS.value,
        default=BusinessType.LOGISTICS,
    )
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    users = relationship("User", back_populates="tenant")
    carriers = relationship("Carrier", back_populates="tenant")
    trips = relationship("Trip", back_populates="tenant")

    @property
    def is_own_fleet(self) -> bool:
        return self.business_type == BusinessType.OWN_FLEET

    @property
    def is_logistics(self) -> bool:
        return self.business_type == BusinessType.LOGISTICS

    @property
    def is_hybrid(self) -> bool:
        return self.business_type == BusinessType.HYBRID
