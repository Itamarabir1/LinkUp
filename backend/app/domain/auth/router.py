import logging

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, get_db
from app.api.dependencies.rate_limit import rate_limit_auth
from app.api.dependencies.services import get_auth_service
from app.core.config import settings
from app.core.exceptions.auth import GoogleAuthFailed
from app.core.exceptions.base import LinkUpError
from app.domain.auth.schema import (
    AuthMessageResponse,
    ChangePasswordRequest,
    EmailOnlyRequest,
    GoogleSignInRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetConfirmResponse,
    RefreshRequest,
    RefreshResponse,
    UserOut,
    UserRegister,
    VerifyEmailRequest,
)
from app.domain.auth.service import AuthService
from app.domain.users.model import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db),
    response: Response = Response(),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """Register a new user (step one: create unverified account)."""
    logger.info("[LinkUp] register called: email=%s", getattr(user_in, "email", ""))
    new_user = await auth_svc.register_new_user(db=db, user_in=user_in)

    # Stash email in cookie for verification (10 minutes)
    response.set_cookie(
        key="pending_verification_email",
        value=new_user.email,
        max_age=600,  # 10 minutes
        httponly=True,
        secure=getattr(settings, "FORCE_HTTPS_REDIRECT", False),  # Secure flag in HTTPS only
        samesite="lax",
    )

    return new_user


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    return await auth_svc.request_password_reset(db, email=email)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="התחברות (Access Token)",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """
    Authenticate and return a short-lived **access_token** plus **refresh_token**.

    Validates user exists, password matches, and `is_verified`.
    Response includes JWT access token, rotated refresh token, `token_type: bearer`, and user info.

    **Swagger:** run Login, copy `access_token`, click Authorize, paste token for protected routes.

    Clients send `Authorization: Bearer <access_token>` on protected APIs and call POST /auth/refresh
    with the stored refresh token when the access token expires.
    """
    return await auth_svc.authenticate_and_create_token(
        db=db,
        email=data.email,
        password=data.password,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="רענון Access Token",
)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """
    Exchange the refresh token from login for a new access token and rotated refresh token.

    Previous refresh tokens are invalidated; only the latest hash in DB is valid.
    Returns 401 (`InvalidRefreshTokenError`) when the token is wrong, expired, or not in DB.
    """
    return await auth_svc.refresh_access_token(db, refresh_token=data.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="התנתקות (Logout)",
)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """Revoke refresh token(s) for the user (logout until next password login)."""
    auth_header = request.headers.get("Authorization") or ""
    access_token = None
    if auth_header.lower().startswith("bearer "):
        access_token = auth_header[7:].strip()
    await auth_svc.logout(db, user=current_user, access_token=access_token)


def _frontend_base_url() -> str:
    return getattr(settings, "FRONTEND_URL", "https://linkup.co.il").rstrip("/")


@router.get("/verify-email/confirm")
async def verify_email_by_link(
    email: str = Query(..., description="כתובת המייל לאימות"),
    code: str = Query(..., description="קוד האימות מהמייל"),
    db: AsyncSession = Depends(get_db),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """Email verification via one-click link; redirects to frontend on success or error."""
    base = _frontend_base_url()
    try:
        await auth_svc.verify_user_email(db, email, code)
        return RedirectResponse(url=f"{base}/verified", status_code=302)
    except Exception:
        return RedirectResponse(url=f"{base}/verify-email?error=invalid", status_code=302)


@router.post("/verify-email", response_model=AuthMessageResponse)
async def verify_email(
    data: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    response: Response = Response(),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """
    Verify email from the SPA using a typed code.
    Email may come from the registration cookie or from the request body.
    """
    # Fallback email from cookie
    email = data.email
    if not email:
        email = request.cookies.get("pending_verification_email")
        if not email:
            from app.core.exceptions.user import UserNotFoundError

            raise UserNotFoundError()

    result = await auth_svc.verify_user_email(db, email, data.code)

    # Clear pending cookie after success
    response.delete_cookie(
        key="pending_verification_email",
        httponly=True,
        secure=getattr(settings, "FORCE_HTTPS_REDIRECT", False),
        samesite="lax",
    )

    return result


@router.post("/resend-verification", response_model=AuthMessageResponse)
async def resend_verification_code(
    data: EmailOnlyRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """Resend email verification code."""
    return await auth_svc.initiate_email_verification(db, data.email)


@router.post("/password-reset/request", response_model=AuthMessageResponse)
async def request_password_reset(
    data: EmailOnlyRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """Password reset step 1: request OTP emailed to the user."""
    return await auth_svc.request_password_reset(db, data.email)


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """Password reset step 2: email + OTP + new password (twice)."""
    return await auth_svc.reset_password_with_code(
        db=db,
        email=data.email,
        code=data.code,
        new_password=data.new_password,
    )


@router.post("/change-password", response_model=AuthMessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """
    Authenticated password change with old password + new password confirmation.
    Same strength rules as registration.
    """
    return await auth_svc.change_password(db, user_id=current_user.user_id, data=data)


@router.post(
    "/google-signin",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="התחברות דרך Google OAuth",
)
async def google_signin(
    data: GoogleSignInRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """
    Google Sign-In: verify ID token from the client, auto-provision user if new.

    Returns the same token bundle as password /login.
    """
    try:
        # Ensure GOOGLE_CLIENT_ID is configured
        if not settings.GOOGLE_CLIENT_ID:
            logger.error("GOOGLE_CLIENT_ID not configured in settings")
            raise GoogleAuthFailed(message="שירות Google לא מוגדר בשרת")

        return await auth_svc.authenticate_with_google(db=db, id_token=data.id_token)
    except LinkUpError:
        raise
    except Exception as e:
        logger.exception("Error in google_signin endpoint: %s", e)
        raise GoogleAuthFailed() from e
