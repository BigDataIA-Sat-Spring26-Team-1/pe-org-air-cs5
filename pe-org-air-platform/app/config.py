import os
from typing import Optional, Literal

try:
    from pydantic import SecretStr
    from pydantic_settings import BaseSettings, SettingsConfigDict

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
            extra="ignore",
        )

    settings = Settings()

except (ImportError, Exception):
    # Fallback for environments where pydantic-settings / pydantic v2 is not
    # available (e.g. Airflow containers that pin pydantic<2).
    # Reads directly from environment variables with sensible defaults.
    class _SimpleSettings:
        APP_NAME: str = "PE Org-AI-R Platform"
        APP_VERSION: str = "1.0.0"
        APP_ENV: str = os.getenv("APP_ENV", "development")
        DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
        SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-default")

        PATENTSVIEW_API_KEY: Optional[str] = os.getenv("PATENTSVIEW_API_KEY")
        WEXTRACTOR_API_KEY: Optional[str] = os.getenv("WEXTRACTOR_API_KEY")
        SEC_API_KEY: Optional[str] = os.getenv("SEC_API_KEY")

        SNOWFLAKE_ACCOUNT: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
        SNOWFLAKE_USER: str = os.getenv("SNOWFLAKE_USER", "")
        SNOWFLAKE_PASSWORD: str = os.getenv("SNOWFLAKE_PASSWORD", "")
        SNOWFLAKE_DATABASE: str = os.getenv("SNOWFLAKE_DATABASE", "PE_ORGAIR")
        SNOWFLAKE_SCHEMA: str = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
        SNOWFLAKE_WAREHOUSE: str = os.getenv("SNOWFLAKE_WAREHOUSE", "")
        SNOWFLAKE_ROLE: str = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")

        REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
        REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
        REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

        AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
        AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
        S3_BUCKET: Optional[str] = os.getenv("S3_BUCKET")
        AWS_FOLDER: str = os.getenv("AWS_FOLDER", "sec")

    settings = _SimpleSettings()
