import os
from enum import Enum
from typing import List

from pydantic import Field  # 👈 ADD THIS IMPORT
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        use_enum_values=True,
        extra="ignore",
    )
    # =========================
    # JWT
    # =========================
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    REFRESH_ROTATION_ENABLED: bool = True
    ACCESS_COOKIE_NAME: str = "sahajomy_access"
    REFRESH_COOKIE_NAME: str = "sahajomy_refresh"
    CSRF_COOKIE_NAME: str = "sahajomy_csrf"

    # =========================
    # DATABASE (Pieces)
    # =========================
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Optional override (not required)
    DATABASE_URL: str | None = None

    # =========================
    # REDIS
    # =========================
    REDIS_URL: str | None = None

    # =========================
    # OTP
    # =========================
    OTP_EXPIRE_MINUTES: int = 10

    # =========================
    # COMMISSION
    # =========================
    DEFAULT_COMMISSION_PERCENTAGE: float = 1.0

    # =========================
    # LOGGING
    # =========================
    LOG_LEVEL: str = "WARNING"
    TRUSTED_PROXY_CIDRS: List[str] = ["172.16.0.0/12"]

    # =========================
    # CLOUDINARY (Required)
    # =========================
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # =========================
    # UPLOAD
    # =========================
    MAX_IMAGE_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    CLAMAV_HOST: str | None = None
    CLAMAV_PORT: int = 3310
    CLAMAV_TIMEOUT_SECONDS: int = 15
    MALWARE_SCAN_REQUIRED: bool = False

    # =========================
    # WHATSAPP CLOUD API (Optional - feature removed)
    # =========================
    WHATSAPP_ACCESS_TOKEN: str | None = Field(
        default=None, description="Meta WhatsApp Access Token"
    )
    WHATSAPP_PHONE_NUMBER_ID: str | None = Field(
        default=None, description="Meta WhatsApp Phone Number ID"
    )
    WHATSAPP_BUSINESS_PHONE: str | None = Field(
        default=None, description="Your business phone number with country code"
    )
    WHATSAPP_VERIFY_TOKEN: str | None = Field(
        default=None, description="Your custom webhook verification token"
    )
    WHATSAPP_API_VERSION: str = "v18.0"
    WHATSAPP_SESSION_EXPIRY: int = 300  # 5 minutes

    # =========================
    # WHATSAPP PHONE ENCRYPTION
    # =========================
    PHONE_ENCRYPTION_KEY: str = Field(
        ..., description="Master key for phone encryption"
    )
    PHONE_HASH_PEPPER: str = Field(..., description="Secret pepper for phone hashing")
    ENCRYPTION_SALT: str = Field(..., description="Salt for key derivation")
    MASK_PHONE_IN_LOGS: bool = True

    # =========================
    # NEW: EMAIL CONFIGURATION
    # =========================
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    EMAIL_SMTP_HOST: str = "smtp-relay.brevo.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USERNAME: str = Field(
        ..., description="Brevo SMTP username - required for email delivery"
    )  # This field is now required
    EMAIL_SMTP_PASSWORD: str = Field(
        ..., description="Brevo SMTP password/API key - required for email delivery"
    )  # This field is now required
    EMAIL_FROM_ADDRESS: str = Field(
        ..., description="Email address to send from - required for email delivery"
    )
    EMAIL_DELIVERY_MODE: str = "brevo"

    # =========================
    # FRONTEND URL
    # =========================
    APP_URL: str | None = None
    FRONTEND_URL: str = "http://localhost:3000"

    # =========================
    # ENVIRONMENT
    # =========================
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT

    # Feature flags
    ENABLE_INSTAGRAM_IMPORT: bool = True
    ENABLE_DIRECT_UPLOAD: bool = True

    # Public Agizisha abuse controls. Keep CAPTCHA optional until the browser
    # widget is configured, but fail closed whenever it is explicitly enabled.
    AGIZISHA_ORDER_MAX_PER_IP_PER_HOUR: int = 10
    AGIZISHA_ORDER_MAX_PER_WHATSAPP_PER_HOUR: int = 3
    AGIZISHA_CAPTCHA_REQUIRED: bool = False
    AGIZISHA_TURNSTILE_SECRET_KEY: str | None = None

    # =========================
    # Build Docker-safe DB URL
    # =========================
    @property
    def database_url(self) -> str:
        # If DATABASE_URL explicitly provided, use it
        if self.DATABASE_URL:
            return self.DATABASE_URL

        # Otherwise build Docker-safe connection string
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}"
            f"@db:5432/{self.POSTGRES_DB}"
        )

    @property
    def public_app_url(self) -> str:
        base_url = (self.APP_URL or self.FRONTEND_URL or "").strip()
        if not base_url:
            base_url = "http://localhost:3000"
        return base_url.rstrip("/")


settings = Settings()
