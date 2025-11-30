"""FastAPI REST API for University Recommendation System."""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from core.config import get_settings
from core.exceptions import BaseError, ErrorCategory
from api.auth import require_api_key

logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Error category to HTTP status code mapping
ERROR_STATUS_MAP = {
    ErrorCategory.VALIDATION: 400,
    ErrorCategory.CONFIGURATION: 400,
    ErrorCategory.API: 502,
    ErrorCategory.DATABASE: 503,
    ErrorCategory.NETWORK: 504,
    ErrorCategory.SCRAPING: 502,
    ErrorCategory.PROCESSING: 500,
    ErrorCategory.SYSTEM: 500,
}

# Pydantic models for API
class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, str] = Field(..., description="Service health status")


class ScrapeRequest(BaseModel):
    """Request model for scraping."""
    urls: List[str] = Field(..., description="URLs to scrape")


# Global services
university_repo = None
program_repo = None
scraper_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global university_repo, program_repo, scraper_service

    # Startup
    try:
        logger.info("Starting University Recommendation API")

        # Initialize services
        settings = get_settings()

        # Database repositories
        from database.repositories import ProgramRepository, UniversityRepository
        university_repo = UniversityRepository()
        program_repo = ProgramRepository()

        # Scraper service
        from services.scraper_service import ScraperService
        scraper_service = ScraperService()

        logger.info("All services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down University Recommendation API")

# Create FastAPI app
app = FastAPI(
    title="University Recommendation System API",
    description="REST API for university program recommendations and data",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Get settings for CORS configuration
settings = get_settings()

# Configure CORS - use specific origins in production
cors_origins = settings.api.cors_origins
is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
if cors_origins == ["*"] and is_production:
    logger.warning("CORS configured with wildcard origin in production - restricting")
    cors_origins = []  # Disable CORS in production if not configured properly

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Exception handlers
@app.exception_handler(BaseError)
async def base_error_handler(request, exc: BaseError):
    """Handle BaseError exceptions with proper HTTP status codes."""
    # Map error category to HTTP status code
    status_code = ERROR_STATUS_MAP.get(exc.category, 500)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "severity": exc.severity.value,
                "category": exc.category.value,
                "operation": exc.context.operation if exc.context else None,
                "component": exc.context.component if exc.context else None
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal details in production
    is_prod = os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred" if is_prod else str(exc)
            }
        }
    )

# API Routes
@app.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    services_status = {}

    # Check database connectivity
    try:
        if program_repo:
            # Simple connectivity check
            count = await program_repo.count()
            services_status["database"] = "healthy"
        else:
            services_status["database"] = "not_initialized"
    except Exception as e:
        services_status["database"] = f"unhealthy: {str(e)}"

    # Overall status
    overall_status = "healthy" if all(
        status in ["healthy", "not_initialized"] for status in services_status.values()
    ) else "unhealthy"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        version="1.0.0",
        services=services_status
    )

@app.get("/stats")
@limiter.limit("30/minute")
async def get_statistics(request: Request):
    """Get system statistics."""
    if not program_repo:
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        # Get counts
        total_programs = await program_repo.count()
        countries = await program_repo.get_distinct_countries()
        program_types = await program_repo.get_distinct_program_types()

        return {
            "total_programs": total_programs,
            "countries_covered": countries,
            "program_types": program_types
        }

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")

@app.get("/universities", tags=["Search"])
@limiter.limit("100/minute")
async def search_universities(
    request: Request,
    q: Optional[str] = Query(None, min_length=1, max_length=200, description="Search query"),
    country: Optional[str] = Query(None, max_length=100, description="Country filter"),
    program_type: Optional[str] = Query(None, max_length=100, description="Program type filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset")
):
    """Search universities with filters."""
    if not university_repo:
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        universities = await university_repo.search_universities(
            query=q,
            country=country,
            program_type=program_type,
            limit=limit,
            offset=offset
        )

        return {
            "results": universities,
            "total": len(universities),  # In production, get total count separately
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to search universities: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/programs", tags=["Search"])
@limiter.limit("100/minute")
async def search_programs(
    request: Request,
    university_name: Optional[str] = Query(None, max_length=200, description="University name filter"),
    program_name: Optional[str] = Query(None, max_length=200, description="Program name filter"),
    degree_level: Optional[str] = Query(None, max_length=50, description="Degree level filter"),
    field_of_study: Optional[str] = Query(None, max_length=100, description="Field of study filter"),
    country: Optional[str] = Query(None, max_length=100, description="Country filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset")
):
    """Search programs with filters."""
    if not program_repo:
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        programs = await program_repo.search_programs(
            university_name=university_name,
            program_name=program_name,
            degree_level=degree_level,
            field_of_study=field_of_study,
            country=country,
            limit=limit,
            offset=offset
        )

        return {
            "results": programs,
            "total": len(programs),  # In production, get total count separately
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to search programs: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/countries")
@limiter.limit("60/minute")
async def get_supported_countries(request: Request):
    """Get list of supported countries."""
    from core.constants import SUPPORTED_COUNTRIES
    return {"countries": SUPPORTED_COUNTRIES}

@app.get("/program-types", tags=["Reference Data"])
@limiter.limit("60/minute")
async def get_supported_program_types(request: Request):
    """Get list of supported program types."""
    from core.constants import SUPPORTED_PROGRAM_TYPES
    return {"program_types": SUPPORTED_PROGRAM_TYPES}


# ============== Admin Endpoints (Require API Key) ==============

@app.post("/admin/scrape", tags=["Admin"], dependencies=[Depends(require_api_key)])
@limiter.limit("10/minute")
async def trigger_scraping(
    request: Request,
    scrape_request: ScrapeRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger web scraping for specified URLs.
    
    Requires API key authentication via X-API-Key header.
    """
    if not scraper_service:
        raise HTTPException(status_code=503, detail="Scraper service not available")

    try:
        background_tasks.add_task(scraper_service.scrape_urls, scrape_request.urls)

        return {
            "message": f"Scraping triggered for {len(scrape_request.urls)} URLs",
            "status": "running",
            "urls": scrape_request.urls
        }

    except Exception as e:
        logger.error(f"Failed to trigger scraping: {e}")
        raise HTTPException(status_code=500, detail="Failed to start scraping")


@app.get("/admin/cache/stats", tags=["Admin"], dependencies=[Depends(require_api_key)])
@limiter.limit("30/minute")
async def get_cache_stats(request: Request):
    """Get cache statistics. Requires API key."""
    try:
        from services.llm_service import LLMService
        llm_service = LLMService()
        stats = await llm_service.get_cache_stats()
        return {"cache_stats": stats}
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")


@app.post("/admin/cache/clear", tags=["Admin"], dependencies=[Depends(require_api_key)])
@limiter.limit("5/minute")
async def clear_cache(request: Request):
    """Clear the LLM response cache. Requires API key."""
    try:
        from services.llm_service import LLMService
        llm_service = LLMService()
        await llm_service.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")