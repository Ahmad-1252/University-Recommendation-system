"""Core module for the University Recommendation System."""

from .config import Settings, get_settings, reload_settings
from .constants import (
    UNIVERSITY_URLS,
    UNIVERSITY_METADATA,
    DEGREE_TYPES,
    PROGRAM_SPECIALIZATIONS,
    LANGUAGE_REQUIREMENTS,
    CURRENCY_CODES,
    APPLICATION_DEADLINES,
    QUALITY_THRESHOLDS,
    EXPORT_CONFIGS,
    LLM_PROMPTS
)
from .exceptions import (
    UniversityScraperError,
    ScrapingError,
    LLMExtractionError,
    ValidationError,
    DatabaseError,
    ConnectionError,
    DuplicateDataError,
    QueryError,
    ConfigurationError,
    APIError,
    GroqAPIError,
    RateLimitError,
    ExportError,
    FileOperationError,
    QualityCheckError
)

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    "reload_settings",

    # Constants
    "UNIVERSITY_URLS",
    "UNIVERSITY_METADATA",
    "DEGREE_TYPES",
    "PROGRAM_SPECIALIZATIONS",
    "LANGUAGE_REQUIREMENTS",
    "CURRENCY_CODES",
    "APPLICATION_DEADLINES",
    "QUALITY_THRESHOLDS",
    "EXPORT_CONFIGS",
    "LLM_PROMPTS",

    # Exceptions
    "UniversityScraperError",
    "ScrapingError",
    "LLMExtractionError",
    "ValidationError",
    "DatabaseError",
    "ConnectionError",
    "DuplicateDataError",
    "QueryError",
    "ConfigurationError",
    "APIError",
    "GroqAPIError",
    "RateLimitError",
    "ExportError",
    "FileOperationError",
    "QualityCheckError"
]