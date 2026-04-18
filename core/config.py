# core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from decimal import Decimal

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis / Celery
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Paystack
    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str
    PAYSTACK_WEBHOOK_SECRET: str
    PAYSTACK_CORPORATE_ACCOUNT_CODE: str

    # WhatsApp
    WHATSAPP_TOKEN: str
    WHATSAPP_PHONE_ID: str
    WHATSAPP_VERIFY_TOKEN: str

    # FingerprintJS
    FPJS_SECRET_API_KEY: str

    # App
    ENVIRONMENT: str = 'development'
    BASE_URL: str
    ESCROW_HOLD_HOURS: int = 12
    PLATFORM_FEE_PERCENT: Decimal = Decimal('4.0')

    class Config:
        env_file = '.env'
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()