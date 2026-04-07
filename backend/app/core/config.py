from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from pydantic import AliasChoices, EmailStr, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# תיקיית backend (היכן ש-.env נמצא) – כך שה-.env נטען גם כשמריצים מ-cwd אחר
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    LinkUp System Settings - Architect Edition (2026).
    ניהול ריכוזי של כל משתני הסביבה עם וולידציה בזמן עלייה.
    מעודכן לתמיכה ב-Kafka KRaft וארכיטקטורת אירועים מלאה.
    """

    # --- Project Metadata ---
    PROJECT_NAME: str = "LinkUp"
    APP_NAME: str = "linkup-backend"
    DEBUG: bool = Field(False)
    ENVIRONMENT: str = Field(
        "development",
        description="שם סביבה (Sentry, לוגים): development / staging / production",
    )
    SENTRY_DSN: str | None = Field(
        None,
        description="Sentry DSN; ריק = ללא שליחה ל-Sentry",
    )
    API_V1_STR: str = "/api/v1"

    # --- PostgreSQL / PostGIS ---
    POSTGRES_USER: str = Field("")
    POSTGRES_PASSWORD: str = Field("")
    POSTGRES_DB: str = Field("")
    POSTGRES_HOST: str = Field("localhost")
    POSTGRES_PORT: str = Field("5432")

    # --- DB Connection Pool ---
    DB_POOL_SIZE: int = Field(5, description="SQLAlchemy pool_size (חיבורים קבועים)")
    DB_MAX_OVERFLOW: int = Field(10, description="חיבורים נוספים תחת עומס")
    DB_POOL_TIMEOUT: int = Field(30, description="שניות המתנה לחיבור פנוי")
    DB_POOL_RECYCLE: int = Field(1800, description="חידוש חיבורים כל 30 דקות")

    # אופציונלי: חיבור מלא ל-Postgres משורת סביבה (למשל מ-K8s/פרודקשן)
    DATABASE_URL_RAW: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "DATABASE_URL_RAW"),
        description="Optional full database URL (e.g. from Kubernetes secret). If set, overrides pieces above.",
    )

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """
        מקור אמת ל-DSN של ה-DB.
        - לוקאלי / Docker: נבנה מ-POSTGRES_*
        - פרודקשן: אם DATABASE_URL (RAW) קיים – משתמשים בו ומוודאים asyncpg.
        """
        if self.DATABASE_URL_RAW:
            url = self.DATABASE_URL_RAW
            # postgresql:// או postgres:// – ממירים ל-postgresql+asyncpg
            if url.startswith("postgres://"):
                return "postgresql+asyncpg://" + url[len("postgres://") :]
            if url.startswith("postgresql://"):
                return "postgresql+asyncpg://" + url[len("postgresql://") :]
            return url

        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # --- Redis ---
    REDIS_HOST: str = Field("localhost")
    REDIS_PORT: int = Field(6379)
    REDIS_DB: int = Field(0)
    REDIS_PASSWORD: str | None = Field(None)
    # Redis DB נפרד לאירועי צ'אט (Pub/Sub completion)
    REDIS_CHAT_DB: int = Field(1)
    # אופציונלי: חיבור Redis מלא (למשל מ-K8s/פרודקשן)
    REDIS_URL_RAW: str | None = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_URL", "REDIS_URL_RAW"),
        description="Optional full Redis URL. If set, overrides REDIS_HOST/PORT/DB/PASSWORD.",
    )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL_RAW:
            return self.REDIS_URL_RAW
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field
    @property
    def REDIS_CHAT_URL(self) -> str:
        """
        אותו host כמו REDIS_URL, DB=REDIS_CHAT_DB (חייב להתאים ל-chat-ws).
        """
        if self.REDIS_URL_RAW:
            try:
                u = urlparse(self.REDIS_URL_RAW)
                netloc = u.netloc
                if not netloc and u.path:
                    return self.REDIS_URL_RAW
                return urlunparse((u.scheme or "redis", netloc, f"/{self.REDIS_CHAT_DB}", "", "", ""))
            except Exception:
                pass
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_CHAT_DB}"

    # --- RabbitMQ (Infrastructure & Celery) ---
    RABBITMQ_HOST: str = Field("localhost")
    RABBITMQ_PORT: int = Field(5672)
    RABBITMQ_USER: str = Field("")
    RABBITMQ_PASSWORD: str = Field("")
    CELERY_TIMEZONE: str = Field("Asia/Jerusalem")

    @computed_field
    @property
    def RABBITMQ_URL(self) -> str:
        """המקור היחיד לאמת עבור RabbitMQ - משמש את ה-Client ואת Celery"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.RABBITMQ_URL

    # --- Frontend & API (לינקים במיילים / כפתורים) ---
    FRONTEND_URL: str = Field(
        "http://localhost:5173",
        description="כתובת האפליקציה (פרונט). לוקאלי: localhost:5173; פרודקשן: הגדר ב-.env (למשל https://linkup.co.il).",
    )
    API_PUBLIC_URL: str = Field(
        "",
        description="כתובת הבקאנד בציבור (למשל https://api.linkup.co.il). אם מוגדר – כפתור אימות במייל יפתח לינק אימות בלחיצה אחת.",
    )

    # --- External Services (Brevo / Sendinblue) ---
    BREVO_API_KEY: str = Field("")
    BREVO_SENDER_EMAIL: EmailStr = Field("support@itamarabir.com")
    BREVO_SENDER_NAME: str = Field("LinkUp", description="שם השולח במיילים")

    # --- EIA (U.S. fuel prices API) ---
    # Get free API key: https://www.eia.gov/opendata/register.php
    EIA_API_KEY: str = Field("", description="EIA Open Data API key for fuel price scanner")

    # --- Google Maps Geocoding API ---
    GOOGLE_MAPS_API_KEY: str = Field(
        "",
        description=(
            "Google Maps API key – Geocoding, Directions, Distance Matrix. גם נשלח לפרונט ל-Maps JavaScript API דרך GET /api/v1/geo/maps-key."
        ),
    )

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = Field(
        "",
        description="Google OAuth 2.0 Client ID מה-Google Cloud Console. נדרש לאימות ID tokens מ-Google Sign-In.",
    )
    GOOGLE_CLIENT_SECRET: str | None = Field(
        None,
        description="Google OAuth 2.0 Client Secret (אופציונלי - נדרש רק אם צריך access tokens, לא ל-ID token verification).",
    )

    # --- Security & Auth (חובה בפרודקשן – בפיתוח ברירת מחדל) ---
    SECRET_KEY: str = Field(
        "",
        description="Must be set in .env for production",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="תוקף Access Token בדקות")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, description="תוקף Refresh Token בימים (לטוקן הארוך)")
    JWT_ISSUER: str = Field("linkup-api", description="JWT claim 'iss' (issuer)")

    # --- HTTPS (פרודקשן מאחורי Proxy) ---
    FORCE_HTTPS_REDIRECT: bool = Field(
        False,
        description="If True, redirect HTTP requests to HTTPS (set when behind a proxy that sets X-Forwarded-Proto).",
    )

    # --- CORS ---
    CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins. If empty, FRONTEND_URL is used.",
    )

    # --- Rate limiting (auth endpoints) ---
    RATE_LIMIT_AUTH_WINDOW_SECONDS: int = Field(60, description="חלון זמן ל-rate limit על auth (שניות)")
    RATE_LIMIT_AUTH_MAX_REQUESTS: int = Field(10, description="מקסימום בקשות ל-auth ל-IP בחלון")

    # --- Cloud Infrastructure (AWS & Firebase) – אופציונלי בפיתוח ---
    AWS_ACCESS_KEY_ID: str = Field("")
    AWS_SECRET_ACCESS_KEY: str = Field("")
    AWS_REGION: str = "eu-central-1"
    S3_BUCKET_NAME: str = Field("")

    CLOUDFRONT_DOMAIN: str | None = Field(
        None,
        description="CloudFront hostname for CDN-backed media GET URLs; if unset, presigned S3 GET is used.",
    )

    @field_validator("CLOUDFRONT_DOMAIN", mode="before")
    @classmethod
    def normalize_cloudfront_domain(cls, v: str | None) -> str | None:
        if not v:
            return None
        if not isinstance(v, str):
            return v
        v = v.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        return v or None

    # --- Upload temp directory (קבצים זמניים לפני העלאה ל-S3) ---
    # ברירת מחדל: תיקיית המערכת (tempfile.gettempdir()). אם מוגדר – משתמשים בתיקייה זו (נוצר אוטומטית אם חסר).
    UPLOAD_TEMP_DIR: str | None = Field(
        None,
        description="Optional directory for upload temp files; default is system temp.",
    )

    FIREBASE_SERVICE_ACCOUNT_PATH: str = Field("", description="Path to Firebase JSON (optional for local dev)")
    FIREBASE_CREDENTIALS_JSON: str | None = Field(None, description="Firebase credentials as JSON string (production)")

    # --- Logging ---
    LOG_LEVEL: str = Field("INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    LOG_FORMAT: str = Field(
        "json",
        description="json (production) or text (local dev)",
    )
    USER_EVENTS_ENABLED: bool = True

    # --- Pydantic Configuration ---
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
