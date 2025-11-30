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
    BaseError,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
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
    DeepSeekAPIError,
    RateLimitError,
    NetworkError,
    TimeoutError,
    ExportError,
    FileOperationError,
    QualityCheckError,
    CacheError,
    CircuitBreakerError
)
from .retry import (
    RetryStrategy,
    RetryConfig,
    RetryPolicy,
    ExponentialBackoffRetry,
    CircuitBreakerRetry,
    retry_with_backoff
)
from .circuit_breaker import (
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerRegistry,
    get_circuit_breaker
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

    # Enhanced Exceptions
    "BaseError",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
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
    "DeepSeekAPIError",
    "RateLimitError",
    "NetworkError",
    "TimeoutError",
    "ExportError",
    "FileOperationError",
    "QualityCheckError",
    "CacheError",
    "CircuitBreakerError",

    # Retry Framework
    "RetryStrategy",
    "RetryConfig",
    "RetryPolicy",
    "ExponentialBackoffRetry",
    "CircuitBreakerRetry",
    "retry_with_backoff",

    # Circuit Breaker
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "get_circuit_breaker"
]