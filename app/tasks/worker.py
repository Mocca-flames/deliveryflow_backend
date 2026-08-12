"""
Taskiq background tasks — notifications, driver pack expiry, sync processing.
"""
from taskiq import TaskiqMessage, TaskiqResult, TaskiqMiddleware
from taskiq_redis import RedisBroker

from app.config import get_settings

settings = get_settings()

broker = RedisBroker(url=settings.REDIS_URL)


class DatabaseMiddleware(TaskiqMiddleware):
    """Middleware to provide database session to tasks."""

    async def pre_execute(self, message: TaskiqMessage) -> None:
        pass

    async def post_execute(
        self,
        message: TaskiqMessage,
        result: TaskiqResult,
    ) -> None:
        pass


broker.add_middleware(DatabaseMiddleware())


@broker.task
async def dispatch_notification(
    channel: str,
    recipient: str,
    subject: str,
    body: str,
    metadata: dict | None = None,
) -> bool:
    """Dispatch notification via configured channel."""
    from app.notifications.dispatcher import notification_dispatcher

    notifier = notification_dispatcher.get_notifier(channel)
    if notifier is None:
        return False

    await notifier.send(
        recipient=recipient,
        subject=subject,
        body=body,
        metadata=metadata or {},
    )
    return True


@broker.task
async def revalidate_drivers_packs() -> int:
    """Check and expire old driver's packs."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.services.drivers_pack import DriversPackService

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        svc = DriversPackService(db)
        count = await svc.check_and_expire()
        await db.commit()
        return count


@broker.task
async def process_sync_events(tenant_id: str) -> int:
    """Process pending sync events for a tenant."""
    from uuid import UUID
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.services.sync import SyncService

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        svc = SyncService(db)
        events = await svc.poll_unprocessed(UUID(tenant_id))
        for event in events:
            await svc.mark_processed(event.id)
        await db.commit()
        return len(events)
