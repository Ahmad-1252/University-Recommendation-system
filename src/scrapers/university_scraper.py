"""Main university scraper implementation."""

import asyncio
import logging
from typing import Optional, List
from crawl4ai import AsyncWebCrawler

from .base_scraper import BaseScraper
from .content_extractor import ContentExtractor
from .link_discoverer import LinkDiscoverer
from ..models.university import UniversityProgram
from ..core.exceptions import ScrapingError
from ..database.repositories import ProgramRepository

logger = logging.getLogger(__name__)


class UniversityScraper(BaseScraper):
    """Main scraper for university program data."""

    def __init__(self,
                 content_extractor: Optional[ContentExtractor] = None,
                 link_discoverer: Optional[LinkDiscoverer] = None,
                 repository: Optional[ProgramRepository] = None):
        super().__init__(name="UniversityScraper")

        self.content_extractor = content_extractor or ContentExtractor()
        self.link_discoverer = link_discoverer or LinkDiscoverer()
        self.repository = repository or ProgramRepository()

    async def scrape_program_data(self, url: str) -> Optional[UniversityProgram]:
        """
        Scrape program data from a single URL.

        Args:
            url: URL to scrape

        Returns:
            UniversityProgram instance if successful
        """
        logger.info(f"Starting scrape of {url}")

        try:
            # Validate URL first
            if not await self.validate_url(url):
                logger.warning(f"URL validation failed: {url}")
                return None

            # Create crawler and extraction strategy
            crawler = AsyncWebCrawler()
            extraction_strategy = self.content_extractor.create_extraction_strategy()

            # Perform the crawl and extraction
            result = await crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy,
                timeout=self.timeout
            )

            if not result.success:
                logger.error(f"Crawl failed for {url}")
                return None

            # Process extracted content
            if result.extracted_content and len(result.extracted_content) > 0:
                # Get the first extracted item (assuming single program per page)
                extracted_data = result.extracted_content[0]

                # Create UniversityProgram instance
                program = UniversityProgram(**extracted_data)
                program.source_url = url

                # Enrich with additional data
                program = self._enrich_program_data(program)

                logger.info(f"Successfully scraped: {program.program_name}")
                return program
            else:
                logger.warning(f"No content extracted from {url}")
                return None

        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            raise ScrapingError(f"Failed to scrape {url}: {e}") from e
        finally:
            # Rate limiting delay
            await asyncio.sleep(self.rate_limit_delay)

    async def validate_url(self, url: str) -> bool:
        """
        Validate if a URL contains program information.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid
        """
        try:
            # Use link discoverer for validation
            valid_urls = await self.link_discoverer.validate_program_urls([url])
            return len(valid_urls) > 0

        except Exception as e:
            logger.error(f"URL validation error for {url}: {e}")
            return False

    async def scrape_university_site(self,
                                   base_url: str,
                                   max_programs: int = 10) -> List[UniversityProgram]:
        """
        Scrape all programs from a university website.

        Args:
            base_url: Base URL of the university
            max_programs: Maximum number of programs to scrape

        Returns:
            List of scraped UniversityProgram instances
        """
        logger.info(f"Starting university site scrape: {base_url}")

        try:
            # Discover program links
            program_links = await self.link_discoverer.discover_program_links(
                base_url, max_pages=max_programs * 2
            )

            # Limit to max_programs
            program_links = program_links[:max_programs]

            if not program_links:
                logger.warning(f"No program links found for {base_url}")
                return []

            # Scrape all discovered links
            scraped_data = await self.scrape_multiple(program_links)

            # Filter out None results and return programs
            programs = [program for program in scraped_data.values() if program is not None]

            logger.info(f"Successfully scraped {len(programs)} programs from {base_url}")
            return programs

        except Exception as e:
            logger.error(f"University site scraping failed for {base_url}: {e}")
            raise ScrapingError(f"Failed to scrape university site {base_url}: {e}") from e

    async def scrape_and_save(self, url: str) -> bool:
        """
        Scrape a URL and save the result to database.

        Args:
            url: URL to scrape

        Returns:
            True if successfully scraped and saved
        """
        try:
            program = await self.scrape_program_data(url)

            if program:
                success = self.repository.save(program)
                if success:
                    logger.info(f"Saved program: {program.program_name}")
                return success
            else:
                logger.warning(f"No program data to save from {url}")
                return False

        except Exception as e:
            logger.error(f"Scrape and save failed for {url}: {e}")
            return False

    async def scrape_multiple_and_save(self, urls: List[str]) -> Dict[str, bool]:
        """
        Scrape multiple URLs and save results to database.

        Args:
            urls: List of URLs to scrape

        Returns:
            Dictionary mapping URLs to success status
        """
        logger.info(f"Starting batch scrape and save of {len(urls)} URLs")

        results = {}

        # Scrape all URLs
        scraped_data = await self.scrape_multiple(urls)

        # Save successful results
        programs_to_save = [
            program for program in scraped_data.values()
            if program is not None
        ]

        if programs_to_save:
            save_results = self.repository.save_many(programs_to_save)

            # Map back to URLs
            saved_count = 0
            for url, program in scraped_data.items():
                if program:
                    results[url] = True
                    saved_count += 1
                else:
                    results[url] = False

            logger.info(f"Batch save completed: {saved_count} programs saved")
        else:
            # All failed
            results = {url: False for url in urls}

        return results

    def get_scraper_stats(self) -> dict:
        """Get scraper statistics and configuration."""
        base_stats = self.get_scraper_info()

        # Add scraper-specific stats
        base_stats.update({
            "content_extractor_cache": self.content_extractor.get_cache_stats(),
            "repository_connected": True  # Could add actual connection check
        })

        return base_stats