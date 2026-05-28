"""Abstract base scraper class for university program scraping."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.config import get_settings
from src.models.university import UniversityProgram

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all university scrapers."""

    def __init__(self, name: str = "BaseScraper"):
        self.name = name
        self.settings = get_settings()
        self.timeout = self.settings.scraping.timeout
        self.max_retries = self.settings.scraping.retry_attempts
        self.rate_limit_delay = self.settings.scraping.retry_backoff_factor
        logger.info(f"Initialized {self.name}")

    @abstractmethod
    async def scrape_program_data(
        self, url: str, skip_validation: bool = False
    ) -> Optional[UniversityProgram]:
        """
        Scrape program data from a given URL.

        Args:
            url: The URL to scrape
            skip_validation: Skip URL validation (use for user-provided URLs)

        Returns:
            UniversityProgram instance if successful, None otherwise

        Raises:
            ScrapingError: If scraping fails after retries
        """
        pass

    @abstractmethod
    async def validate_url(self, url: str) -> bool:
        """
        Validate if a URL is accessible and contains relevant content.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and accessible
        """
        pass

    async def scrape_multiple(
        self, urls: list[str], skip_validation: bool = True
    ) -> Dict[str, Optional[UniversityProgram]]:
        """
        Scrape multiple URLs concurrently.

        Args:
            urls: List of URLs to scrape
            skip_validation: Skip URL validation (True for user-provided URLs)

        Returns:
            Dictionary mapping URLs to UniversityProgram instances or None
        """
        logger.info(f"Starting batch scrape of {len(urls)} URLs")

        # Limit concurrent requests
        semaphore = asyncio.Semaphore(self.settings.scraping.max_concurrent_requests)

        async def scrape_with_semaphore(
            url: str,
        ) -> tuple[str, Optional[UniversityProgram]]:
            async with semaphore:
                try:
                    result = await self.scrape_program_data(
                        url, skip_validation=skip_validation
                    )
                    return url, result
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {e}")
                    return url, None

        # Execute all scrapes concurrently
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        scraped_data = {}
        successful = 0
        failed = 0

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                continue

            url, program = result
            scraped_data[url] = program

            if program:
                successful += 1
            else:
                failed += 1

        logger.info(f"Batch scrape completed: {successful} successful, {failed} failed")
        return scraped_data

    def _calculate_confidence_score(self, program: UniversityProgram) -> float:
        """
        Calculate confidence score based on data completeness and quality.

        Args:
            program: UniversityProgram instance

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base score from data completeness
        base_score = program.data_completeness

        # Bonus for having key fields
        bonuses = 0.0

        # Critical fields bonus
        critical_fields = [
            program.program_name,
            program.university_name,
            program.country,
            program.program_description,
        ]
        if all(critical_fields):
            bonuses += 0.1

        # Academic requirements bonus
        if program.gpa_requirement_min is not None or any(
            [
                program.language_requirements.toefl_min,
                program.language_requirements.ielts_min,
            ]
        ):
            bonuses += 0.1

        # Financial information bonus
        if program.tuition_fees.international_per_year is not None:
            bonuses += 0.1

        # Rankings bonus
        if any(
            [
                program.rankings.qs_world_ranking,
                program.rankings.the_world_ranking,
                program.rankings.us_news_ranking,
            ]
        ):
            bonuses += 0.05

        # Cap bonuses at 0.3
        bonuses = min(bonuses, 0.3)

        confidence = min(base_score + bonuses, 1.0)
        return round(confidence, 3)

    def _enrich_program_data(self, program: UniversityProgram) -> UniversityProgram:
        """
        Enrich program data with additional information.

        Args:
            program: UniversityProgram instance to enrich

        Returns:
            Enriched UniversityProgram instance
        """
        # Calculate confidence score
        program.confidence_score = self._calculate_confidence_score(program)

        # Set last updated timestamp
        program.last_updated = datetime.now(datetime.UTC)

        # Add any additional enrichment logic here
        # (e.g., currency conversion, ranking lookups, etc.)

        return program

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Retry a function using the centralized retry framework.
        """
        from src.core.retry import retry_with_backoff

        return await retry_with_backoff(
            func,
            max_attempts=self.max_retries + 1,
            initial_delay=1.0,
            backoff_factor=2.0,
            jitter=True,
            *args,
            **kwargs,
        )

    def get_scraper_info(self) -> Dict[str, Any]:
        """
        Get information about this scraper.

        Returns:
            Dictionary with scraper information
        """
        return {
            "name": self.name,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rate_limit_delay": self.rate_limit_delay,
            "max_concurrent_requests": self.settings.scraping.max_concurrent_requests,
        }
