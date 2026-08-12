"""
Authentication service — JWT generation, login, token refresh.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.core.exceptions import DeliveryFlowError

settings = get_settings()


class AuthenticationError(DeliveryFlowError):
    """Raised when authentication fails."""
    pass


def create_access_token(user_id: UUID, tenant_id: UUID | None = None) -> str:
    """Create JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id) if tenant_id else None,
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """Create JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRES_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def authenticate_user(db: AsyncSession, login: LoginRequest) -> TokenResponse:
    """Authenticate user and return tokens."""
    stmt = select(User).where(User.email == login.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(login.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is deactivated")

    access_token = create_access_token(user.id, user.tenant_id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


async def refresh_tokens(db: AsyncSession, refresh: RefreshRequest) -> TokenResponse:
    """Refresh access token using refresh token."""
    from jose import JWTError

    try:
        payload = jwt.decode(
            refresh.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token")

    except JWTError:
        raise AuthenticationError("Invalid or expired refresh token")

    user = await db.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    access_token = create_access_token(user.id, user.tenant_id)
    new_refresh_token = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )
