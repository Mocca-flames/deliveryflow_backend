import logging

import httpx

from app.config import get_settings
from app.notifications.email.base import EmailProvider, QuotaExceededError

logger = logging.getLogger(__name__)
settings = get_settings()

MAILJET_API_URL = "https://api.mailjet.com/v3/send"


class MailjetProvider(EmailProvider):
    """Mailjet transactional email provider."""

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> None:
        payload: dict = {
            "FromEmail": settings.MAILJET_SENDER_EMAIL,
            "FromName": settings.MAILJET_SENDER_NAME,
            "Recipients": [{"Email": to}],
            "Subject": subject,
            "Html-part": html_content,
        }
        if text_content:
            payload["Text-part"] = text_content

        auth = (settings.MAILJET_API_KEY, settings.MAILJET_API_SECRET)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                MAILJET_API_URL, json=payload, auth=auth, timeout=30
            )

        if resp.status_code == 200:
            logger.info("Mailjet email sent to %s", to)
            return

        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        logger.error("Mailjet raw response: %s", body)
        error_msg = body.get("ErrorMessage", str(body))

        if resp.status_code == 401:
            logger.warning("Mailjet quota/permission denied: %s", error_msg)
            raise QuotaExceededError(f"Mailjet quota exceeded: {error_msg}")

        logger.error("Mailjet API error %s: %s", resp.status_code, error_msg)
        raise RuntimeError(f"Mailjet email failed ({resp.status_code}): {error_msg}")

    @property
    def name(self) -> str:
        return "mailjet"

    async def is_configured(self) -> bool:
        return bool(settings.MAILJET_API_KEY and settings.MAILJET_API_SECRET and settings.MAILJET_SENDER_EMAIL)
