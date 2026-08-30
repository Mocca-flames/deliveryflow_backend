"""
Sync event service — process offline sync events from Flutter outbox.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_event import SyncEvent


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_batch(self, tenant_id: UUID, events: list[dict]) -> list[SyncEvent]:
        """Process a batch of sync events from Flutter outbox."""
        processed = []

        for event_data in events:
            # Check idempotency
            stmt = select(SyncEvent).where(
                SyncEvent.idempotency_key == event_data["idempotency_key"],
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                processed.append(existing)
                continue

            event = SyncEvent(
                tenant_id=tenant_id,
                trip_id=UUID(event_data["trip_id"]),
                event_uuid=UUID(event_data["event_uuid"]),
                device_id=event_data["device_id"],
                event_type=event_data["event_type"],
                payload=event_data["payload"],
                idempotency_key=event_data["idempotency_key"],
                processed=False,
                created_at=datetime.now(UTC),
            )
            self.db.add(event)
            processed.append(event)

        await self.db.flush()
        return processed

    async def poll_unprocessed(self, tenant_id: UUID, limit: int = 100) -> list[SyncEvent]:
        """Poll unprocessed events for a tenant."""
        stmt = (
            select(SyncEvent)
            .where(
                SyncEvent.tenant_id == tenant_id,
                not SyncEvent.processed,
            )
            .order_by(SyncEvent.created_at)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_processed(self, event_id: UUID) -> None:
        """Mark an event as processed."""
        event = await self.db.get(SyncEvent, event_id)
        if event:
            event.processed = True
            event.processed_at = datetime.now(UTC)
            await self.db.flush()
