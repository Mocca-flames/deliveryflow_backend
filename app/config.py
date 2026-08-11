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
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
