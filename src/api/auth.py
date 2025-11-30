"""API authentication and security utilities."""

import logging
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

from core.config import get_settings

logger = logging.getLogger(__name__)

# API Key header configuration
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Validate API key from request header.
    
    Args:
        api_key: The API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    settings = get_settings()
    
    # If no API key is configured, allow all requests (development mode)
    if not settings.api.api_key:
        logger.warning("API key not configured - running in open mode")
        return "open_mode"
    
    if not api_key:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'X-API-Key' header."
        )
    
    if api_key != settings.api.api_key:
        logger.warning(f"Invalid API key attempt")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return api_key


async def require_api_key(api_key: str = Depends(get_api_key)) -> str:
    """Dependency that requires a valid API key."""
    return api_key


async def optional_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Optional API key validation - doesn't fail if missing.
    Useful for public endpoints that have enhanced features with auth.
    """
    settings = get_settings()
    
    if not api_key:
        return None
    
    if settings.api.api_key and api_key == settings.api.api_key:
        return api_key
    
    return None
