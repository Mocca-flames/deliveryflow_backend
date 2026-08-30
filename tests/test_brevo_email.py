"""
Email Provider Test Script — verifies Brevo and Mailjet implementations.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.notifications.email.brevo import BrevoProvider
from app.notifications.email.mailjet import MailjetProvider

RECIPIENTS = [
    "juniorflamebet@gmail.com",
    "juniorbypassfrp@gmail.com",
    "marothi.tech@gmail.com",
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #f8f9fa; border-radius: 8px; padding: 30px; text-align: center;">
        <h2 style="color: #333; margin-bottom: 10px;">DeliveryFlow</h2>
        <p style="color: #666; font-size: 16px;">{provider} Email Test</p>
        <div style="background: #fff; border: 2px solid #28a745; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <p style="font-size: 18px; color: #28a745; font-weight: bold;">Email sent successfully!</p>
        </div>
        <p style="color: #999; font-size: 14px;">This is a test email from DeliveryFlow.</p>
    </div>
</body>
</html>
"""


async def test_provider(provider, sender_email, provider_name):
    print(f"\n{'=' * 50}")
    print(f"Testing: {provider_name}")
    print(f"Sender: {sender_email}")
    print(f"{'=' * 50}")

    if not await provider.is_configured():
        print(f"[SKIP] {provider_name} not configured")
        return 0, 0

    success_count = 0
    fail_count = 0

    for recipient in RECIPIENTS:
        try:
            await provider.send(
                to=recipient,
                subject=f"DeliveryFlow - {provider_name} Email Test",
                html_content=HTML_TEMPLATE.format(provider=provider_name),
                text_content=f"{provider_name} Email Test - This is a test email from DeliveryFlow.",
            )
            print(f"[OK] Sent to {recipient}")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] Failed to {recipient}: {e}")
            fail_count += 1

    print(f"Results: {success_count} sent, {fail_count} failed")
    return success_count, fail_count


async def main():
    settings = get_settings()

    # Test Brevo
    brevo = BrevoProvider()
    b_ok, b_fail = await test_provider(brevo, settings.BREVO_SENDER_EMAIL, "Brevo")

    # Test Mailjet
    mailjet = MailjetProvider()
    m_ok, m_fail = await test_provider(mailjet, settings.MAILJET_SENDER_EMAIL, "Mailjet")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"SUMMARY: Brevo {b_ok}/{b_ok+b_fail} | Mailjet {m_ok}/{m_ok+m_fail}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())