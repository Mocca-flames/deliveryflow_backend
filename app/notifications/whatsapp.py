"""
WhatsApp Notifier — Meta Cloud API adapter.
Phase 2 implementation. Interface ready for integration.
"""
from typing import Any

from app.notifications.base import Notifier


class WhatsAppNotifier(Notifier):
    """Meta Cloud API adapter — stub for Phase 2."""

    @property
    def channel_name(self) -> str:
        return "whatsapp"

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        # Phase 2: Implement Meta Cloud API integration
        raise NotImplementedError("WhatsApp integration ships in Phase 2")

    async def is_available(self) -> bool:
        # Phase 2: Check Meta API status
        return False
