"""Enhanced exception classes with error codes, severity levels, and recovery strategies."""

import enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class ErrorSeverity(enum.Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(enum.Enum):
    """Error categories for classification."""
    NETWORK = "network"
    API = "api"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    SCRAPING = "scraping"
    PROCESSING = "processing"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Additional context information for errors."""
    operation: str
    component: str
    metadata: Optional[Dict[str, Any]] = None
    recoverable: bool = True
    retry_count: int = 0


class BaseError(Exception):
    """Enhanced base exception with error codes and context."""

    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or ErrorContext(
            operation="unknown",
            component="unknown"
        )
        self.cause = cause
        self.timestamp = None  # Will be set when logged

    def __str__(self):
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "operation": self.context.operation,
            "component": self.context.component,
            "recoverable": self.context.recoverable,
            "retry_count": self.context.retry_count,
            "metadata": self.context.metadata,
            "cause": str(self.cause) if self.cause else None
        }


# Legacy exceptions for backward compatibility
class UniversityScraperError(BaseError):
    """Base exception for scraping-related errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="SCRAPE_001",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SCRAPING,
            context=context,
            cause=cause
        )


class ScrapingError(UniversityScraperError):
    """Raised when scraping a webpage fails."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        # Call BaseError directly to avoid duplicating error_code
        BaseError.__init__(
            self,
            message=message,
            error_code="SCRAPE_002",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SCRAPING,
            context=context,
            cause=cause
        )


class LLMExtractionError(UniversityScraperError):
    """Raised when LLM extraction fails."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        # Call BaseError directly to avoid duplicating error_code
        BaseError.__init__(
            self,
            message=message,
            error_code="SCRAPE_003",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.PROCESSING,
            context=context,
            cause=cause
        )


class ValidationError(UniversityScraperError):
    """Raised when data validation fails."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        # Call BaseError directly to avoid duplicating error_code
        BaseError.__init__(
            self,
            message=message,
            error_code="VALID_001",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=cause
        )


class DatabaseError(BaseError):
    """Base exception for database-related errors."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="DB_001",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            context=context,
            cause=cause
        )


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        BaseError.__init__(
            self,
            message=message,
            error_code="DB_002",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.DATABASE,
            context=context,
            cause=cause
        )


class DuplicateDataError(DatabaseError):
    """Raised when attempting to save duplicate data."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        BaseError.__init__(
            self,
            message=message,
            error_code="DB_003",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.DATABASE,
            context=context,
            cause=cause
        )


class QueryError(DatabaseError):
    """Raised when database query fails."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        BaseError.__init__(
            self,
            message=message,
            error_code="DB_004",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATABASE,
            context=context,
            cause=cause
        )


class ConfigurationError(BaseError):
    """Raised when configuration is invalid or missing."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_001",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.CONFIGURATION,
            context=context,
            cause=cause
        )


class APIError(BaseError):
    """Base exception for external API errors."""
    def __init__(self, message: str, error_code: str = "API_001", severity: ErrorSeverity = ErrorSeverity.HIGH, category: ErrorCategory = ErrorCategory.API, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=severity,
            category=category,
            context=context,
            cause=cause
        )


class GroqAPIError(APIError):
    """Raised when Groq API calls fail."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="API_002",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.API,
            context=context,
            cause=cause
        )


class DeepSeekAPIError(APIError):
    """Raised when DeepSeek API calls fail."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="API_003",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.API,
            context=context,
            cause=cause
        )


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        BaseError.__init__(
            self,
            message=message,
            error_code="API_004",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.API,
            context=context,
            cause=cause
        )


class NetworkError(BaseError):
    """Raised when network operations fail."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="NET_001",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK,
            context=context,
            cause=cause
        )


class TimeoutError(NetworkError):
    """Raised when operations timeout."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        BaseError.__init__(
            self,
            message=message,
            error_code="NET_002",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.NETWORK,
            context=context,
            cause=cause
        )


class ExportError(BaseError):
    """Raised when data export fails."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="EXPORT_001",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.PROCESSING,
            context=context,
            cause=cause
        )


class FileOperationError(BaseError):
    """Raised when file operations fail."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="FILE_001",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM,
            context=context,
            cause=cause
        )


class QualityCheckError(BaseError):
    """Raised when data quality checks fail."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="QUALITY_001",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=cause
        )


class CacheError(BaseError):
    """Raised when cache operations fail."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="CACHE_001",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.SYSTEM,
            context=context,
            cause=cause
        )


class CircuitBreakerError(BaseError):
    """Raised when circuit breaker is open."""
    def __init__(self, message: str, context: Optional[ErrorContext] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            error_code="CIRCUIT_001",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.SYSTEM,
            context=context,
            cause=cause
        )