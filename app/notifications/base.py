from abc import ABC, abstractmethod
from typing import Any


class Notifier(ABC):
    """Abstract base for notification channel adapters."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send notification via the channel.
        Returns True if sent successfully, False if failed.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the channel is currently available (rate limits, API status)."""
        ...

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the channel identifier (e.g., 'whatsapp', 'sms', 'email')."""
        ...
