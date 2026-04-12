import logging

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, get_db
from app.api.dependencies.rate_limit import rate_limit_auth
from app.api.dependencies.services import get_auth_service
from app.core.config import settings
from app.core.exceptions.auth import GoogleAuthFailed
from app.core.exceptions.base import LinkupError
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
    """רישום משתמש חדש - השלב הראשון"""
    logger.info("[Linkup] register נקרא: email=%s", getattr(user_in, "email", ""))
    print("[Linkup] register endpoint – מתחיל register_new_user")
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
    אימות משתמש והנפקת **Access Token** (קצר) + **Refresh Token** (ארוך).

    - **email** = אימייל המשתמש.
    - **password** = סיסמה.
    - בודק קיום משתמש, סיסמה נכונה ו־`is_verified`.
    - מחזיר `access_token` (JWT קצר תוקף), `refresh_token` (JWT ארוך תוקף), `token_type: bearer` ופרטי משתמש.

    **שימוש ב-Swagger:**
    1. בצע Login וקבל את ה-`access_token`.
    2. לחץ על כפתור ה-Authorize (המנעול) למעלה.
    3. הדבק את ה-`access_token` בשדה.
    4. מהיום הזה, כל הבקשות המוגנות ב-Swagger יעבדו אוטומטית.

    הלקוח ישלח את **access_token** בכל בקשה מוגנת: `Authorization: Bearer <access_token>`.
    את **refresh_token** שומרים (למשל ב־storage) ומשתמשים ב־POST /auth/refresh לקבלת access_token חדש.
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
    מקבל **Refresh Token** (שנשמר ב-login) ומחזיר **Access Token** חדש + **Refresh Token** חדש (רוטציה).

    הטוקן הישן מתבטל – רק הטוקן האחרון ששמור ב-DB תקף. שגיאה: `InvalidRefreshTokenError` (401) אם הטוקן שגוי/פג/לא תואם ל-DB.
    """
    return await auth_svc.refresh_access_token(db, refresh_token=data.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="התנתקות (Logout)",
)
async def logout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """מבטל את ה-Refresh Token של המשתמש – התנתקות (לא יוכל לקבל Access Token חדש עד login מחדש)."""
    await auth_svc.logout(db, user=current_user)


def _frontend_base_url() -> str:
    return getattr(settings, "FRONTEND_URL", "https://linkup.co.il").rstrip("/")


@router.get("/verify-email/confirm")
async def verify_email_by_link(
    email: str = Query(..., description="כתובת המייל לאימות"),
    code: str = Query(..., description="קוד האימות מהמייל"),
    db: AsyncSession = Depends(get_db),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """אימות בלחיצה אחת – הלינק מהכפתור במייל. מפנה לפרונט (הצלחה או שגיאה)."""
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
    auth_svc: AuthService = Depends(get_auth_service),
):
    """
    אימות המייל מהפרונט (המשתמש מזין קוד בדף).
    האימייל יכול לבוא מה-cookie (אחרי רישום) או מה-body (אם לא נשמר ב-cookie).
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
    """שליחה חוזרת של קוד האימות"""
    return await auth_svc.initiate_email_verification(db, data.email)


@router.post("/password-reset/request", response_model=AuthMessageResponse)
async def request_password_reset(
    data: EmailOnlyRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_auth),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """שחזור סיסמה – שלב 1: המשתמש מזין מייל, נשלח אליו קוד במייל."""
    return await auth_svc.request_password_reset(db, data.email)


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
    auth_svc: AuthService = Depends(get_auth_service),
):
    """שחזור סיסמה – שלב 2: המשתמש מזין מייל + קוד מהמייל + סיסמה חדשה פעמיים."""
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
    שינוי סיסמה למשתמש מחובר: סיסמה ישנה + סיסמה חדשה פעמיים (אישור).
    ולידציה כמו ברישום: חוזק סיסמה + התאמה בין שני שדות הסיסמה החדשה.
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
    התחברות/רישום דרך Google OAuth.

    מקבל ID token מ-Google Sign-In (הפרונט שולח את ה-token שהתקבל מ-Google).
    השרת מאמת את ה-token עם Google, ואם המשתמש לא קיים - יוצר משתמש חדש אוטומטית (auto-signup).

    מחזיר access_token + refresh_token + user (כמו /login רגיל).
    """
    try:
        # Ensure GOOGLE_CLIENT_ID is configured
        if not settings.GOOGLE_CLIENT_ID:
            logger.error("GOOGLE_CLIENT_ID not configured in settings")
            raise GoogleAuthFailed(message="שירות Google לא מוגדר בשרת")

        return await auth_svc.authenticate_with_google(db=db, id_token=data.id_token)
    except LinkupError:
        raise
    except Exception as e:
        logger.exception("Error in google_signin endpoint: %s", e)
        raise GoogleAuthFailed() from e
