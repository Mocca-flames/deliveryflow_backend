import logging

import httpx

from app.config import get_settings
from app.notifications.email.base import EmailProvider, QuotaExceededError

logger = logging.getLogger(__name__)
settings = get_settings()

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoProvider(EmailProvider):
    """Brevo (Sendinblue) transactional email provider."""

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> None:
        payload: dict = {
            "sender": {
                "email": settings.BREVO_SENDER_EMAIL,
                "name": settings.BREVO_SENDER_NAME,
            },
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html_content,
        }
        if text_content:
            payload["textContent"] = text_content

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": settings.BREVO_API_KEY,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)

        if resp.status_code == 201:
            logger.info("Brevo email sent to %s", to)
            return

        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        message = body.get("message", "")

        if resp.status_code in (402, 403) or "quota" in message.lower() or "credit" in message.lower():
            logger.warning("Brevo quota exceeded: %s", message)
            raise QuotaExceededError(f"Brevo quota exceeded: {message}")

        logger.error("Brevo API error %s: %s", resp.status_code, message)
        raise RuntimeError(f"Brevo email failed ({resp.status_code}): {message}")

    @property
    def name(self) -> str:
        return "brevo"

    async def is_configured(self) -> bool:
        return bool(settings.BREVO_API_KEY and settings.BREVO_SENDER_EMAIL)
