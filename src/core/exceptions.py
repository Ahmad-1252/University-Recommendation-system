"""Custom exception classes for the University Recommendation System."""


class UniversityScraperError(Exception):
    """Base exception for scraping-related errors."""
    pass


class ScrapingError(UniversityScraperError):
    """Raised when scraping a webpage fails."""
    pass


class LLMExtractionError(UniversityScraperError):
    """Raised when LLM extraction fails."""
    pass


class ValidationError(UniversityScraperError):
    """Raised when data validation fails."""
    pass


class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class DuplicateDataError(DatabaseError):
    """Raised when attempting to save duplicate data."""
    pass


class QueryError(DatabaseError):
    """Raised when database query fails."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class APIError(Exception):
    """Base exception for external API errors."""
    pass


class GroqAPIError(APIError):
    """Raised when Groq API calls fail."""
    pass


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    pass


class ExportError(Exception):
    """Raised when data export fails."""
    pass


class FileOperationError(Exception):
    """Raised when file operations fail."""
    pass


class QualityCheckError(Exception):
    """Raised when data quality checks fail."""
    pass