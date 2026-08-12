from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "DeliveryFlow"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://df_user:df_password@localhost:5432/deliveryflow"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRES_DAYS: int = 7

    # Object Storage (SeaweedFS S3-compatible)
    S3_ENDPOINT: str = "http://localhost:8333"
    S3_ACCESS_KEY: str = "seaweed"
    S3_SECRET_KEY: str = "seaweed"
    S3_BUCKET: str = "deliveryflow"
    S3_REGION: str = "us-east-1"

    # Notifications
    WHATSAPP_API_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""

    # Driver's Pack
    DRIVERS_PACK_EXPIRY_DAYS: int = 365

    # LLM Document Extraction (multi-provider)
    LLM_ENABLED: bool = True
    LLM_PROVIDERS: str = "mistral,google"  # comma-separated priority order

    # Mistral (primary)
    MISTRAL_API_KEY: str = ""
    MISTRAL_VISION_MODEL: str = "ministral-14b-latest"

    # Google Gemini (fallback)
    GOOGLE_API_KEY: str = ""
    GOOGLE_VISION_MODEL: str = "gemini-2.5-flash"

    # OpenRouter (optional fallback)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_VISION_MODEL: str = "openai/gpt-4o-mini"

    # LLM concurrency control
    LLM_MAX_CONCURRENT_PAGES: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
