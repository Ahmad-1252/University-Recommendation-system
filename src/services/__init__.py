"""Services for the University Recommendation System."""

__all__ = [
    "LLMService",
    "CachedLLMService",
    "ValidationService",
    "EnrichmentService",
    "ScraperService",
    "cache"
]

def __getattr__(name):
    """Lazy import to avoid circular imports and relative import issues."""
    if name == "LLMService":
        from .llm_service import LLMService
        return LLMService
    elif name == "CachedLLMService":
        from .cached_llm_service import CachedLLMService
        return CachedLLMService
    elif name == "ValidationService":
        from .validation_service import ValidationService
        return ValidationService
    elif name == "EnrichmentService":
        from .enrichment_service import EnrichmentService
        return EnrichmentService
    elif name == "ScraperService":
        from .scraper_service import ScraperService
        return ScraperService
    elif name == "cache":
        from . import cache
        return cache
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")