"""
Notification service — dispatch notifications via configured channels.
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.dispatcher import notification_dispatcher
from app.core.exceptions import NotificationError


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict | None = None,
    ) -> bool:
        """Send notification via specified channel."""
        try:
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
        except Exception as e:
            raise NotificationError(f"Failed to send notification: {e}")

    async def send_trip_update(
        self,
        trip_id: UUID,
        channel: str,
        recipient: str,
        status: str,
        message: str,
    ) -> bool:
        """Send trip status update notification."""
        return await self.send(
            channel=channel,
            recipient=recipient,
            subject=f"Trip Update: {status}",
            body=message,
            metadata={"trip_id": str(trip_id), "status": status},
        )

    async def send_invoice_notification(
        self,
        invoice_id: UUID,
        channel: str,
        recipient: str,
        invoice_number: str,
        amount: str,
        currency: str,
    ) -> bool:
        """Send invoice notification."""
        return await self.send(
            channel=channel,
            recipient=recipient,
            subject=f"Invoice {invoice_number}",
            body=f"Invoice {invoice_number} for {currency} {amount} has been issued.",
            metadata={"invoice_id": str(invoice_id), "invoice_number": invoice_number},
        )
