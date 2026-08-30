from typing import Any

from app.notifications.base import Notifier


class ConsoleNotifier(Notifier):
    """Logs notifications to stdout — default for development."""

    @property
    def channel_name(self) -> str:
        return "console"

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        print("[NOTIFICATION] Channel: console")
        print(f"  To: {recipient}")
        print(f"  Subject: {subject}")
        print(f"  Body: {body}")
        if metadata:
            print(f"  Metadata: {metadata}")
        return True

    async def is_available(self) -> bool:
        return True
