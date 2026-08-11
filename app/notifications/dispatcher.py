"""
NotificationDispatcher — unified interface for all notification channels.
Channels are pluggable adapters behind this interface.
"""
from typing import Any

from app.notifications.base import Notifier
from app.notifications.console import ConsoleNotifier


class NotificationDispatcher:
    """Dispatches notifications through the appropriate channel adapter."""

    def __init__(self) -> None:
        self._notifiers: dict[str, Notifier] = {}

    def register(self, notifier: Notifier) -> None:
        """Register a notification adapter."""
        self._notifiers[notifier.channel_name] = notifier

    def get(self, channel: str) -> Notifier | None:
        return self._notifiers.get(channel)

    async def send(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send notification via the specified channel.
        Falls back to console if channel unavailable.
        Returns True if sent, False if all channels failed.
        """
        notifier = self._notifiers.get(channel)
        if notifier is None:
            # Fallback to console
            console = self._notifiers.get("console")
            if console:
                return await console.send(recipient, subject, body, metadata)
            return False

        if not await notifier.is_available():
            # Channel unavailable — try console fallback
            console = self._notifiers.get("console")
            if console and console.channel_name != channel:
                return await console.send(recipient, subject, body, metadata)
            return False

        return await notifier.send(recipient, subject, body, metadata)


# Singleton dispatcher
dispatcher = NotificationDispatcher()
dispatcher.register(ConsoleNotifier())
