"""Centralized configuration management for the University Recommendation System."""

from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """MongoDB database configuration."""

    connection_string: str = Field(
        "mongodb://localhost:27017", alias="MONGO_CONNECTION_STRING"
    )
    database_name: str = Field("university_db", alias="DATABASE_NAME")
    collection_name: str = Field("programs", alias="COLLECTION_NAME")
    connection_timeout: int = Field(30)
    max_pool_size: int = Field(10)

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class LLMSettings(BaseSettings):
    """LLM API configuration."""

    provider: str = Field(
        "deepseek", alias="LLM_PROVIDER"
    )  # deepseek (primary) or groq (fallback)
    max_retries: int = Field(3)
    temperature: float = Field(0.1)

    # Provider-specific settings
    groq: "GroqSettings" = Field(default_factory=lambda: GroqSettings())
    deepseek: "DeepSeekSettings" = Field(default_factory=lambda: DeepSeekSettings())

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class GroqSettings(BaseSettings):
    """Groq provider configuration."""

    api_key: str = Field("", alias="GROQ_API_KEY")
    model: str = Field("llama-3.3-70b-versatile", alias="GROQ_MODEL")
    timeout: int = Field(30, alias="GROQ_TIMEOUT")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class DeepSeekSettings(BaseSettings):
    """DeepSeek provider configuration."""

    api_key: str = Field("", alias="DEEPSEEK_API_KEY")
    model: str = Field("deepseek-chat", alias="DEEPSEEK_MODEL")
    timeout: int = Field(30, alias="DEEPSEEK_TIMEOUT")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class ScrapingSettings(BaseSettings):
    """Web scraping configuration."""

    timeout: int = Field(30, alias="SCRAPE_TIMEOUT")
    max_concurrent_requests: int = Field(5, alias="MAX_CONCURRENT_REQUESTS")
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        alias="USER_AGENT",
    )
    retry_attempts: int = Field(3)
    retry_backoff_factor: float = Field(1.0, alias="RATE_LIMIT_DELAY")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field("INFO", alias="LOG_LEVEL")
    format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_path: Optional[str] = Field("logs/app.log")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class ExportSettings(BaseSettings):
    """Data export configuration."""

    output_directory: str = Field("data/exports", alias="EXPORT_DIR")
    supported_formats: List[str] = Field(["csv", "json", "xlsx"])

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class APISettings(BaseSettings):
    """FastAPI REST API configuration."""

    host: str = Field("0.0.0.0", alias="API_HOST")
    port: int = Field(8000, alias="API_PORT")
    api_key: str = Field("", alias="API_KEY")
    rate_limit: int = Field(100, alias="API_RATE_LIMIT")  # requests per period
    rate_limit_period: int = Field(60, alias="API_RATE_LIMIT_PERIOD")  # seconds
    enable_cors: bool = Field(True)
    cors_origins: List[str] = Field(["*"])

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class RedisSettings(BaseSettings):
    """Redis caching configuration."""

    host: str = Field("localhost", alias="REDIS_HOST")
    port: int = Field(6379, alias="REDIS_PORT")
    db: int = Field(0, alias="REDIS_DB")
    password: Optional[str] = Field(None, alias="REDIS_PASSWORD")
    ttl: int = Field(3600, alias="REDIS_TTL")  # Default TTL in seconds
    max_connections: int = Field(10, alias="REDIS_MAX_CONNECTIONS")
    decode_responses: bool = Field(True)

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class ErrorHandlingSettings(BaseSettings):
    """Error handling and resilience configuration."""

    # Retry settings
    default_max_retries: int = Field(3, alias="DEFAULT_MAX_RETRIES")
    default_retry_delay: float = Field(1.0, alias="DEFAULT_RETRY_DELAY")
    default_max_retry_delay: float = Field(60.0, alias="DEFAULT_MAX_RETRY_DELAY")
    default_backoff_factor: float = Field(2.0, alias="DEFAULT_BACKOFF_FACTOR")

    # Circuit breaker settings
    circuit_failure_threshold: int = Field(5, alias="CIRCUIT_FAILURE_THRESHOLD")
    circuit_recovery_timeout: float = Field(60.0, alias="CIRCUIT_RECOVERY_TIMEOUT")
    circuit_success_threshold: int = Field(3, alias="CIRCUIT_SUCCESS_THRESHOLD")
    circuit_timeout: float = Field(30.0, alias="CIRCUIT_TIMEOUT")

    # Error handling
    enable_circuit_breakers: bool = Field(True, alias="ENABLE_CIRCUIT_BREAKERS")
    enable_retry_logging: bool = Field(True, alias="ENABLE_RETRY_LOGGING")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


class Settings(BaseSettings):
    """Main application settings."""

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    scraping: ScrapingSettings = ScrapingSettings()
    logging: LoggingSettings = LoggingSettings()
    export: ExportSettings = ExportSettings()
    redis: RedisSettings = RedisSettings()
    api: APISettings = APISettings()
    error_handling: ErrorHandlingSettings = ErrorHandlingSettings()

    # Application metadata
    app_name: str = "University Recommendation System"
    version: str = "1.0.0"
    debug: bool = Field(False, alias="DEBUG")

    # Project paths
    project_root: Path = Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        """Get data directory path."""
        return self.project_root / "data"

    @property
    def logs_dir(self) -> Path:
        """Get logs directory path."""
        return self.project_root / "logs"

    @property
    def exports_dir(self) -> Path:
        """Get exports directory path."""
        return self.project_root / "data" / "exports"

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, env_prefix="", extra="ignore"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global settings
    settings = Settings()
    return settings
