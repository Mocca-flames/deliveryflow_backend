"""
Authentication API routes — login, refresh tokens, OTP verification, registration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.deps import get_current_user, get_db, get_email_router
from app.models.user import User
from app.notifications.email.router import EmailRouter
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResendOtpRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.services.auth import AuthenticationError, authenticate_user, refresh_tokens
from app.services.otp import (
    OtpError,
    clear_otp,
    send_password_reset_otp,
    send_verification_otp,
    verify_otp,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return access/refresh tokens."""
    try:
        tokens = await authenticate_user(db, body)
        return tokens
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    try:
        tokens = await refresh_tokens(db, body)
        return tokens
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_email_verified": user.is_email_verified,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
    }


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    email_router: EmailRouter = Depends(get_email_router),
):
    """Register a new user and send verification OTP."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="tenant_staff",
        is_active=True,
        is_email_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    try:
        await send_verification_otp(db, body.email, email_router)
    except OtpError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Account created but OTP sending failed: {e}",
        )

    return MessageResponse(message="Registration successful. Please check your email for the verification code.")


@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp_endpoint(
    body: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify the OTP code sent to the user's email."""
    try:
        user = await verify_otp(db, body.email, body.otp)
        user.is_email_verified = True
        await clear_otp(db, user)
    except OtpError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MessageResponse(message="Email verified successfully.")


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(
    body: ResendOtpRequest,
    db: AsyncSession = Depends(get_db),
    email_router: EmailRouter = Depends(get_email_router),
):
    """Resend OTP to the user's email."""
    try:
        await send_verification_otp(db, body.email, email_router)
    except OtpError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MessageResponse(message="A new verification code has been sent to your email.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    email_router: EmailRouter = Depends(get_email_router),
):
    """Send password reset OTP to email."""
    try:
        await send_password_reset_otp(db, body.email, email_router)
    except OtpError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return MessageResponse(message="If an account with that email exists, a password reset code has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using OTP."""
    try:
        user = await verify_otp(db, body.email, body.otp)
        user.password_hash = hash_password(body.new_password)
        await clear_otp(db, user)
    except OtpError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return MessageResponse(message="Password has been reset successfully.")
