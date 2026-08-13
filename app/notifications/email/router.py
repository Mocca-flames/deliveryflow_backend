import logging
import random

from app.notifications.email.base import EmailProvider, QuotaExceededError

logger = logging.getLogger(__name__)


class EmailRouter:
    """
    Routes email through available providers with random selection.
    If a provider's quota is exhausted, it's marked depleted and the other is used.
    If both are depleted, no email is sent and False is returned.
    """

    def __init__(self, providers: list[EmailProvider]) -> None:
        self._providers = providers
        self._depleted: set[str] = set()

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """
        Send email via a randomly selected available provider.
        Returns True if sent successfully, False if all providers failed or are depleted.
        """
        available = [p for p in self._providers if p.name not in self._depleted]

        if not available:
            logger.error("All email providers depleted — cannot send to %s", to)
            return False

        random.shuffle(available)

        for provider in available:
            try:
                await provider.send(to, subject, html_content, text_content)
                return True
            except QuotaExceededError:
                logger.warning("Email provider %s quota exceeded, marking depleted", provider.name)
                self._depleted.add(provider.name)
            except Exception as exc:
                logger.error("Email provider %s failed: %s", provider.name, exc)

        return False

    async def send_otp(self, to: str, otp_code: str) -> bool:
        """Send an OTP email using the router."""
        subject = "Your DeliveryFlow Verification Code"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #f8f9fa; border-radius: 8px; padding: 30px; text-align: center;">
                <h2 style="color: #333; margin-bottom: 10px;">DeliveryFlow</h2>
                <p style="color: #666; font-size: 16px;">Your verification code is:</p>
                <div style="background: #fff; border: 2px dashed #007bff; border-radius: 8px;
                            padding: 20px; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; color: #007bff;
                                 letter-spacing: 8px;">{otp_code}</span>
                </div>
                <p style="color: #999; font-size: 14px;">
                    This code expires in 10 minutes.<br>
                    If you didn't request this, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        text_content = f"Your DeliveryFlow verification code is: {otp_code}. Expires in 10 minutes."
        return await self.send(to, subject, html_content, text_content)

    def reset_depleted(self) -> None:
        """Reset all depleted providers (e.g., on app restart or scheduled task)."""
        self._depleted.clear()
        logger.info("All email providers reset to available")
