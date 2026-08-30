"""
Tracking service — public tracking link data.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import TokenNotFoundError
from app.models.document import Document
from app.models.trip import Trip


class TrackingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_tracking_data(self, token: str) -> dict:
        """Get tracking data for a public link."""
        stmt = select(Trip).where(Trip.tracking_token == token)
        result = await self.db.execute(stmt)
        trip = result.scalar_one_or_none()

        if trip is None:
            raise TokenNotFoundError("Invalid tracking link")

        # Get uploaded documents
        doc_stmt = select(Document).where(
            Document.trip_id == trip.id,
            Document.verified.is_(True),
        )
        doc_result = await self.db.execute(doc_stmt)
        documents = list(doc_result.scalars().all())

        return {
            "trip_id": str(trip.id),
            "reference": trip.reference,
            "status": trip.status,
            "origin": trip.origin,
            "destination": trip.destination,
            "carrier_name": trip.carrier.name if trip.carrier else None,
            "pickup_date": str(trip.pickup_date) if trip.pickup_date else None,
            "delivery_date": str(trip.delivery_date) if trip.delivery_date else None,
            "milestones": self._build_milestones(trip),
            "documents": [
                {
                    "id": str(doc.id),
                    "doc_type": doc.doc_type,
                    "filename": doc.filename,
                    "verified": doc.verified,
                }
                for doc in documents
            ],
        }

    async def get_tracking_status(self, token: str) -> dict:
        """Get minimal status for polling."""
        stmt = select(Trip).where(Trip.tracking_token == token)
        result = await self.db.execute(stmt)
        trip = result.scalar_one_or_none()

        if trip is None:
            raise TokenNotFoundError("Invalid tracking link")

        return {
            "trip_id": str(trip.id),
            "status": trip.status,
            "updated_at": str(trip.updated_at),
        }

    def _build_milestones(self, trip: Trip) -> list[dict]:
        """Build milestone list from trip status."""
        milestones = []
        status_order = ["draft", "assigned", "in_transit", "completed"]

        current_idx = status_order.index(trip.status) if trip.status in status_order else 0

        for i, status in enumerate(status_order):
            milestones.append({
                "status": status,
                "reached": i <= current_idx,
                "label": status.replace("_", " ").title(),
            })

        return milestones
