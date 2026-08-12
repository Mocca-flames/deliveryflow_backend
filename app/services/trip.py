"""
Trip service — CRUD operations and lifecycle management.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import Trip
from app.models.document import TripDocumentRequirement
from app.core.documents import get_required_doc_types
from app.core.token import generate_tracking_token, generate_carrier_token
from app.core.exceptions import DeliveryFlowError, DriverPackGateError
from app.schemas.trip import TripCreate, TripAssign
from app.config import get_settings

settings = get_settings()


class TripService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: UUID, data: TripCreate) -> Trip:
        """Create a new trip with document requirements."""
        now = datetime.now(timezone.utc)
        trip = Trip(
            tenant_id=tenant_id,
            reference=data.reference,
            status="draft",
            origin=data.origin,
            destination=data.destination,
            client_name=data.client_name,
            client_email=data.client_email,
            client_phone=data.client_phone,
            cargo_desc=data.cargo_desc,
            cargo_weight_kg=data.cargo_weight_kg,
            quoted_amount=data.quoted_amount,
            currency=data.currency,
            pickup_date=data.pickup_date,
            delivery_date=data.delivery_date,
            notes=data.notes,
            tracking_token=generate_tracking_token(),
            carrier_token=generate_carrier_token(),
            created_at=now,
            updated_at=now,
        )
        self.db.add(trip)
        await self.db.flush()

        # Auto-create document requirements based on route
        doc_types = get_required_doc_types(data.origin, data.destination)
        for doc_type in doc_types:
            req = TripDocumentRequirement(
                tenant_id=tenant_id,
                trip_id=trip.id,
                doc_type=doc_type,
                required=True,
                uploaded=False,
                category=self._get_category(doc_type),
                created_at=now,
                updated_at=now,
            )
            self.db.add(req)

        await self.db.flush()
        return trip

    async def list(
        self,
        tenant_id: UUID,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
    ) -> tuple[list[Trip], int]:
        """List trips with pagination."""
        stmt = select(Trip).where(Trip.tenant_id == tenant_id)
        count_stmt = select(func.count()).select_from(Trip).where(Trip.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(Trip.status == status)
            count_stmt = count_stmt.where(Trip.status == status)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar()

        stmt = stmt.order_by(Trip.created_at.desc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(stmt)
        trips = list(result.scalars().all())

        return trips, total

    async def get(self, trip_id: UUID, tenant_id: UUID) -> Trip | None:
        """Get a trip by ID."""
        stmt = select(Trip).where(Trip.id == trip_id, Trip.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def assign(self, trip: Trip, data: TripAssign) -> Trip:
        """Assign carrier, driver, and vehicle to trip."""
        from app.state_machines.drivers_pack import check_pack_gate

        # Check driver pack gate before assigning
        pack_valid = await check_pack_gate(self.db, data.driver_id, data.vehicle_id)
        if not pack_valid:
            raise DriverPackGateError(
                "Driver or vehicle has pending/expired KYC pack. Cannot assign."
            )

        trip.carrier_id = data.carrier_id
        trip.driver_id = data.driver_id
        trip.vehicle_id = data.vehicle_id
        trip.status = "assigned"
        trip.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return trip

    async def begin_transit(self, trip: Trip) -> Trip:
        """Mark trip as in transit."""
        trip.status = "in_transit"
        trip.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return trip

    async def complete(self, trip: Trip) -> Trip:
        """Mark trip as completed."""
        trip.status = "completed"
        trip.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return trip

    async def cancel(self, trip: Trip) -> Trip:
        """Cancel trip."""
        trip.status = "cancelled"
        trip.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return trip

    async def get_doc_checklist(self, trip_id: UUID, tenant_id: UUID) -> dict:
        """Get document checklist for a trip."""
        from sqlalchemy import select
        from app.models.document import TripDocumentRequirement, Document

        stmt = select(TripDocumentRequirement).where(
            TripDocumentRequirement.trip_id == trip_id,
            TripDocumentRequirement.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        requirements = list(result.scalars().all())

        total_required = sum(1 for r in requirements if r.required)
        uploaded = sum(1 for r in requirements if r.uploaded)
        missing = [r.doc_type for r in requirements if r.required and not r.uploaded]

        return {
            "trip_id": trip_id,
            "total_required": total_required,
            "uploaded": uploaded,
            "missing": missing,
            "is_complete": len(missing) == 0,
            "requirements": requirements,
        }

    def _get_category(self, doc_type: str) -> str:
        """Map doc_type to category."""
        from app.core.documents import get_category
        return get_category(doc_type)
