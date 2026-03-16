from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "PE Org-AI-R Platform"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"
    SECRET_KEY: SecretStr
    
    # External API Keys
    PATENTSVIEW_API_KEY: SecretStr = None
    WEXTRACTOR_API_KEY: SecretStr = None
    SEC_API_KEY: Optional[SecretStr] = None
    
    # Snowflake
    SNOWFLAKE_ACCOUNT: str
    SNOWFLAKE_USER: str
    SNOWFLAKE_PASSWORD: SecretStr
    SNOWFLAKE_DATABASE: str = "PE_ORGAIR"
    SNOWFLAKE_SCHEMA: str = "PUBLIC"
    SNOWFLAKE_WAREHOUSE: str
    SNOWFLAKE_ROLE: Optional[str] = "ACCOUNTADMIN"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    # AWS S3
    AWS_ACCESS_KEY_ID: SecretStr = None
    AWS_SECRET_ACCESS_KEY: SecretStr = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: Optional[str] = None
    AWS_FOLDER: str = "sec"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()