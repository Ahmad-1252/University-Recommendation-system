"""Centralized configuration management for the University Recommendation System."""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


"""Centralized configuration management for the University Recommendation System."""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class DatabaseSettings(BaseSettings):
    """MongoDB database configuration."""

    connection_string: str = Field("mongodb://localhost:27017", alias="MONGO_CONNECTION_STRING")
    database_name: str = Field("university_db", alias="DATABASE_NAME")
    collection_name: str = Field("programs", alias="COLLECTION_NAME")
    connection_timeout: int = Field(30)
    max_pool_size: int = Field(10)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="", extra="ignore")


class LLMSettings(BaseSettings):
    """Groq LLM API configuration."""

    api_key: str = Field("", alias="GROQ_API_KEY")
    model: str = Field("llama3-70b-8192", alias="GROQ_MODEL")
    timeout: int = Field(30, alias="LLM_TIMEOUT")
    max_retries: int = Field(3)
    temperature: float = Field(0.1)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="", extra="ignore")


class ScrapingSettings(BaseSettings):
    """Web scraping configuration."""

    timeout: int = Field(30, alias="SCRAPE_TIMEOUT")
    max_concurrent_requests: int = Field(5, alias="MAX_CONCURRENT_REQUESTS")
    user_agent: str = Field("UniversityRecommendationBot/1.0")
    retry_attempts: int = Field(3)
    retry_backoff_factor: float = Field(1.0, alias="RATE_LIMIT_DELAY")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="", extra="ignore")


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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="", extra="ignore")


class ExportSettings(BaseSettings):
    """Data export configuration."""

    output_directory: str = Field("data/exports", alias="EXPORT_DIR")
    supported_formats: List[str] = Field(["csv", "json", "xlsx"])

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="", extra="ignore")


class Settings(BaseSettings):
    """Main application settings."""

    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    scraping: ScrapingSettings = ScrapingSettings()
    logging: LoggingSettings = LoggingSettings()
    export: ExportSettings = ExportSettings()

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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_prefix="", extra="ignore")


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