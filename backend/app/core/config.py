from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from pydantic import AliasChoices, EmailStr, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Backend directory (where .env lives) so .env loads even when cwd differs
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    LinkUp system settings (2026).
    Centralized env vars with validation at startup.
    """

    # --- Project Metadata ---
    PROJECT_NAME: str = "LinkUp"
    APP_NAME: str = "linkup-backend"
    DEBUG: bool = Field(False)
    API_DOCS_ENABLED: bool = Field(False, description="Enable Swagger/OpenAPI docs. Set True only in dev/staging.")
    ENVIRONMENT: str = Field(
        "development",
        description="Environment name (Sentry, logs): development / staging / production",
    )
    SENTRY_DSN: str | None = Field(
        None,
        description="Sentry DSN; empty = no Sentry",
    )
    API_V1_STR: str = "/api/v1"

    # --- PostgreSQL / PostGIS ---
    POSTGRES_USER: str = Field("")
    POSTGRES_PASSWORD: str = Field("")
    POSTGRES_DB: str = Field("")
    POSTGRES_HOST: str = Field("localhost")
    POSTGRES_PORT: str = Field("5432")

    # --- DB Connection Pool ---
    DB_POOL_SIZE: int = Field(5, description="SQLAlchemy pool_size (persistent connections)")
    DB_MAX_OVERFLOW: int = Field(10, description="Extra connections under load")
    DB_POOL_TIMEOUT: int = Field(30, description="Seconds to wait for a free connection")
    DB_POOL_RECYCLE: int = Field(1800, description="Recycle connections every 30 minutes")
    DB_STATEMENT_TIMEOUT_MS: int = Field(
        30000,
        description=(
            "Per-session Postgres statement_timeout (ms). Applied via SQLAlchemy "
            "connect_args -> asyncpg server_settings in app/db/session.py. "
            "Alembic 017 sets a fixed 60000ms role-level ceiling (defense-in-depth)."
        ),
    )

    # Optional: full Postgres URL from env (e.g. K8s / production)
    DATABASE_URL_RAW: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "DATABASE_URL_RAW"),
        description="Optional full database URL (e.g. from Kubernetes secret). If set, overrides pieces above.",
    )

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """
        Canonical DB DSN.
        - Local / Docker: built from POSTGRES_*
        - Production: if DATABASE_URL (RAW) is set, use it and ensure asyncpg driver.
        """
        if self.DATABASE_URL_RAW:
            url = self.DATABASE_URL_RAW
            # postgresql:// or postgres:// → normalize to postgresql+asyncpg
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
    REDIS_SENTINEL_HOST: str = Field("", description="Sentinel hostname")
    REDIS_SENTINEL_PORT: int = Field(26379)
    REDIS_MASTER_NAME: str = Field("mymaster")
    # Separate Redis DB for chat events (Pub/Sub completion)
    REDIS_CHAT_DB: int = Field(1)
    # Optional: full Redis URL (e.g. K8s / production)
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
        Same host as REDIS_URL, DB=REDIS_CHAT_DB (must match chat-ws).
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
        """Single source of truth for RabbitMQ — used by client and Celery."""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.RABBITMQ_URL

    # --- Frontend & API (email links / buttons) ---
    FRONTEND_URL: str = Field(
        "http://localhost:5173",
        description="Frontend app URL. Local: localhost:5173; production: set in .env (e.g. https://linkup.co.il).",
    )
    API_PUBLIC_URL: str = Field(
        "",
        description="Public backend URL (e.g. https://api.linkup.co.il). If set, email verify button opens one-click link.",
    )

    # --- External Services (Brevo / Sendinblue) ---
    BREVO_API_KEY: str = Field("")
    BREVO_SENDER_EMAIL: EmailStr = Field("support@itamarabir.com")
    BREVO_SENDER_NAME: str = Field("LinkUp", description="Sender display name in emails")
    EMAIL_RENDERER_URL: str = Field(
        "http://email-renderer:3001",
        description="React Email HTTP service (Compose service name; K8s: http://linkup-email-renderer:3001).",
    )

    # --- EIA (U.S. fuel prices API) ---
    # Get free API key: https://www.eia.gov/opendata/register.php
    EIA_API_KEY: str = Field("", description="EIA Open Data API key for fuel price scanner")

    # --- Google Maps Geocoding API ---
    GOOGLE_MAPS_API_KEY: str = Field(
        "",
        description=(
            "Google Maps API key — Geocoding, Directions, Distance Matrix. Also returned to frontend for Maps JS via GET /api/v1/geo/maps-key."
        ),
    )

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = Field(
        "",
        description="Google OAuth 2.0 Client ID from Google Cloud Console. Required to verify ID tokens from Google Sign-In.",
    )
    GOOGLE_CLIENT_SECRET: str | None = Field(
        None,
        description="Google OAuth 2.0 Client Secret (optional — only if access tokens are needed, not for ID token verification).",
    )

    # --- Security & Auth (required in production; defaults in dev) ---
    SECRET_KEY: str = Field(
        "",
        description="Must be set in .env for production",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="Access token TTL in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, description="Refresh token TTL in days (long-lived token)")
    JWT_ISSUER: str = Field("linkup-api", description="JWT claim 'iss' (issuer)")

    # --- HTTPS (production behind proxy) ---
    FORCE_HTTPS_REDIRECT: bool = Field(
        False,
        description="If True, redirect HTTP requests to HTTPS (set when behind a proxy that sets X-Forwarded-Proto).",
    )

    # --- CORS ---
    CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins. If empty, FRONTEND_URL is used.",
    )

    # --- Rate limiting ---
    # Auth uses sliding-window log (no burst — anti-bruteforce). Chat uses
    # token bucket (burst-tolerant API throttle). Two algorithms by design;
    # see docs/FEATURE_DECISIONS.md (rate-limit-token-bucket).
    RATE_LIMIT_AUTH_WINDOW_SECONDS: int = Field(60, description="Auth sliding-window length (seconds)")
    RATE_LIMIT_AUTH_MAX_PER_WINDOW: int = Field(
        10,
        description="Max auth requests per IP per sliding window",
        validation_alias=AliasChoices("RATE_LIMIT_AUTH_MAX_PER_WINDOW", "RATE_LIMIT_AUTH_MAX_REQUESTS"),
    )
    RATE_LIMIT_CHAT_BUCKET_CAPACITY: int = Field(30, description="Token-bucket capacity for chat per user")
    RATE_LIMIT_CHAT_REFILL_PER_SEC: float = Field(0.5, description="Tokens added per second to chat bucket (0.5 = 30/min)")

    # --- Cloud (AWS & Firebase) — optional in local dev ---
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

    # --- Upload temp directory (staging before S3 upload) ---
    # Default: system temp (tempfile.gettempdir()). If set, use this path (created if missing).
    UPLOAD_TEMP_DIR: str | None = Field(
        None,
        description="Optional directory for upload temp files; default is system temp.",
    )

    FIREBASE_SERVICE_ACCOUNT_PATH: str = Field("", description="Path to Firebase JSON (optional for local dev)")
    FIREBASE_CREDENTIALS_JSON: str | None = Field(None, description="Firebase credentials as JSON string (production)")

    # --- Stripe ---
    STRIPE_SECRET_KEY: str = Field("", description="Stripe secret key (sk_test_... or sk_live_...)")
    STRIPE_WEBHOOK_SECRET: str = Field("", description="Stripe webhook signing secret (whsec_...)")
    BILLING_RECONCILER_ENABLED: bool = Field(True)
    BILLING_RECONCILER_INTERVAL_SECONDS: int = Field(600)
    BILLING_PENDING_MIN_AGE_MINUTES: int = Field(10)
    BILLING_PENDING_MAX_AGE_HOURS: int = Field(24)
    BILLING_IDEMPOTENCY_TTL_HOURS: int = Field(24)

    # --- Logging ---
    LOG_LEVEL: str = Field("INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    LOG_FORMAT: str = Field(
        "json",
        description="json (production) or text (local dev)",
    )
    USER_EVENTS_ENABLED: bool = True
    ADMIN_CAPABILITIES_JSON: str = Field(
        "",
        description="Optional JSON map from admin email to allowed capabilities. Empty = full admin access.",
    )

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
