"""
OTP service — generate, store, verify one-time passwords for email verification.
"""
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.notifications.email.base import QuotaExceededError
from app.notifications.email.router import EmailRouter

logger = logging.getLogger(__name__)
settings = get_settings()


class OtpError(Exception):
    """Raised when OTP operations fail."""


def generate_otp(length: int | None = None) -> str:
    """Generate a cryptographically secure numeric OTP."""
    length = length or settings.OTP_LENGTH
    return "".join(secrets.choice("0123456789") for _ in range(length))


async def create_otp(db: AsyncSession, user: User) -> str:
    """
    Generate a new OTP, hash it, store on user, set expiry.
    Returns the plaintext OTP for sending.
    """
    otp_code = generate_otp()
    user.otp_code = hash_password(otp_code)
    user.otp_expires_at = datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return otp_code


async def verify_otp(db: AsyncSession, email: str, otp: str) -> User:
    """
    Verify OTP for the given email.
    Returns the user if valid, raises OtpError otherwise.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise OtpError("User not found")

    if user.otp_code is None:
        raise OtpError("No OTP pending. Please request a new one.")

    if user.otp_expires_at is None or user.otp_expires_at < datetime.now(UTC):
        raise OtpError("OTP has expired. Please request a new one.")

    if not verify_password(otp, user.otp_code):
        raise OtpError("Invalid OTP code")

    return user


async def clear_otp(db: AsyncSession, user: User) -> None:
    """Clear OTP fields after successful verification."""
    user.otp_code = None
    user.otp_expires_at = None
    db.add(user)
    await db.commit()


async def send_verification_otp(
    db: AsyncSession, email: str, email_router: EmailRouter
) -> None:
    """
    Generate OTP for a user and send it via email.
    Raises OtpError if user not found or email sending fails.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise OtpError("User not found")

    otp_code = await create_otp(db, user)

    try:
        sent = await email_router.send_otp(email, otp_code)
        if not sent:
            raise OtpError("Email sending failed. Please try again later.")
    except QuotaExceededError:
        logger.error("All email providers depleted — cannot send OTP to %s", email)
        raise OtpError("Email service unavailable. Please try again later.")


async def send_password_reset_otp(
    db: AsyncSession, email: str, email_router: EmailRouter
) -> None:
    """
    Generate OTP for password reset and send it via email.
    Raises OtpError if user not found or email sending fails.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Silently return to prevent email enumeration
        logger.info("Password reset requested for non-existent email: %s", email)
        return

    otp_code = await create_otp(db, user)

    try:
        sent = await email_router.send_otp(email, otp_code)
        if not sent:
            raise OtpError("Email sending failed. Please try again later.")
    except QuotaExceededError:
        logger.error("All email providers depleted — cannot send OTP to %s", email)
        raise OtpError("Email service unavailable. Please try again later.")
