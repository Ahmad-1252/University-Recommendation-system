"""Main university scraper implementation."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from crawl4ai import AsyncWebCrawler

from src.core.exceptions import ScrapingError
from src.database.repositories import ProgramRepository, UniversityRepository
from src.models.university import UniversityProgram

from .base_scraper import BaseScraper
from .content_extractor import ContentExtractor
from .link_discoverer import LinkDiscoverer

logger = logging.getLogger(__name__)


class UniversityScraper(BaseScraper):
    """Main scraper for university program data."""

    def __init__(
        self,
        content_extractor: Optional[ContentExtractor] = None,
        link_discoverer: Optional[LinkDiscoverer] = None,
        repository: Optional[ProgramRepository] = None,
        university_repository: Optional[UniversityRepository] = None,
    ):
        super().__init__(name="UniversityScraper")

        self.content_extractor = content_extractor or ContentExtractor()
        self.link_discoverer = link_discoverer or LinkDiscoverer()
        self.repository = repository or ProgramRepository()
        self.university_repository = university_repository or UniversityRepository()

        # Track aggregated university data during scraping
        self._aggregated_university_data: Dict[str, Dict[str, Any]] = {}

    async def scrape_program_data(
        self, url: str, skip_validation: bool = False
    ) -> Optional[UniversityProgram]:
        """
        Scrape program data from a single URL.

        Args:
            url: URL to scrape
            skip_validation: Skip URL validation (use when URL is provided directly by user)

        Returns:
            UniversityProgram instance if successful
        """
        logger.info(f"Starting scrape of {url}")

        try:
            # Validate URL first (unless skipped)
            if not skip_validation and not await self.validate_url(url):
                logger.warning(f"URL validation failed: {url}")
                return None

            # Create crawler
            async with AsyncWebCrawler() as crawler:
                # Perform the crawl
                result = await crawler.arun(url=url, timeout=self.timeout)

                if not result.success:
                    logger.error(
                        f"Crawl failed for {url}: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}"
                    )
                    return None

                # Get HTML content
                html_content = (
                    result.html if hasattr(result, "html") else result.cleaned_html
                )

                if not html_content or len(html_content) < 100:
                    logger.warning(f"No HTML content retrieved from {url}")
                    return None

                logger.info(f"Retrieved {len(html_content)} chars of HTML from {url}")

                # Extract program data using LLM
                program = await self.content_extractor.extract_program_data(
                    url, html_content
                )

                if program:
                    # Enrich with additional data
                    program = self._enrich_program_data(program)
                    logger.info(f"Successfully scraped: {program.program_name}")

                    # Also extract and aggregate university data
                    await self._extract_and_aggregate_university_data(
                        program.university_name, url, html_content
                    )

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

    async def scrape_university_site(
        self, base_url: str, max_programs: int = 10
    ) -> List[UniversityProgram]:
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
            programs = [
                program for program in scraped_data.values() if program is not None
            ]

            logger.info(
                f"Successfully scraped {len(programs)} programs from {base_url}"
            )
            return programs

        except Exception as e:
            logger.error(f"University site scraping failed for {base_url}: {e}")
            raise ScrapingError(
                f"Failed to scrape university site {base_url}: {e}"
            ) from e

    async def scrape_all_programs_from_directory(
        self,
        directory_url: str,
        base_url: str = None,
        category_filter: str = None,
        max_programs: int = 100,
        concurrent: int = 3,
        program_url_pattern: str = None,
        pagination: dict = None,
    ) -> List[UniversityProgram]:
        """
        Discover and scrape ALL programs from a university course directory.

        Args:
            directory_url: URL of the course listing/directory page
            base_url: Base URL for resolving relative links
            category_filter: Optional filter for specific program category
            max_programs: Maximum number of programs to scrape
            concurrent: Number of concurrent scraping tasks
            program_url_pattern: Regex pattern to identify valid program URLs
            pagination: Pagination config dict with 'type', 'pattern', 'max_pages'

        Returns:
            List of successfully scraped UniversityProgram instances
        """
        logger.info(f"Discovering all programs from directory: {directory_url}")

        # Discover all program links
        program_links = await self.link_discoverer.discover_all_program_links(
            directory_url,
            base_url=base_url,
            category_filter=category_filter,
            program_url_pattern=program_url_pattern,
            pagination=pagination,
        )

        if not program_links:
            logger.warning(f"No program links discovered from {directory_url}")
            return []

        logger.info(f"Found {len(program_links)} program links to scrape")

        # Limit programs if needed
        if len(program_links) > max_programs:
            logger.info(f"Limiting to first {max_programs} programs")
            program_links = program_links[:max_programs]

        # Extract just the URLs for scraping
        urls_to_scrape = [p["program_url"] for p in program_links]

        # Scrape all program pages
        all_programs = []

        # Process in batches to respect rate limits
        for i in range(0, len(urls_to_scrape), concurrent):
            batch = urls_to_scrape[i : i + concurrent]
            logger.info(f"Processing batch {i//concurrent + 1}: {len(batch)} programs")

            # Scrape batch
            scraped_data = await self.scrape_multiple(batch)

            for url, program in scraped_data.items():
                if program:
                    # Find the original program info for additional metadata
                    original_info = next(
                        (p for p in program_links if p["program_url"] == url), None
                    )
                    if original_info:
                        # Add discovered metadata if not already set
                        if (
                            not program.program_category
                            or program.program_category == "Other"
                        ):
                            program.program_category = original_info.get(
                                "category", "Other"
                            )
                        if (
                            not program.degree_level
                            or program.degree_level == "Masters"
                        ):
                            program.degree_level = original_info.get(
                                "degree_level", "Unknown"
                            )

                    all_programs.append(program)

            # Rate limiting between batches
            if i + concurrent < len(urls_to_scrape):
                await asyncio.sleep(2)

        logger.info(
            f"Successfully scraped {len(all_programs)} programs from {directory_url}"
        )
        return all_programs

    async def scrape_all_programs_and_save(
        self,
        directory_url: str,
        base_url: str = None,
        category_filter: str = None,
        max_programs: int = 100,
        program_url_pattern: str = None,
        pagination: dict = None,
    ) -> Dict[str, any]:
        """
        Discover, scrape, and save ALL programs from a course directory.

        Args:
            directory_url: URL of the course directory
            base_url: Base URL for resolving relative links
            category_filter: Filter programs by category
            max_programs: Maximum number of programs to scrape
            program_url_pattern: Regex pattern to match program URLs (university-specific)
            pagination: Pagination config dict with 'type', 'pattern', 'max_pages'

        Returns:
            Dictionary with statistics about the operation
        """
        stats = {
            "directory_url": directory_url,
            "programs_discovered": 0,
            "programs_scraped": 0,
            "programs_saved": 0,
            "failed": 0,
            "categories": {},
        }

        # Scrape all programs
        programs = await self.scrape_all_programs_from_directory(
            directory_url,
            base_url=base_url,
            category_filter=category_filter,
            max_programs=max_programs,
            program_url_pattern=program_url_pattern,
            pagination=pagination,
        )

        stats["programs_scraped"] = len(programs)

        # Count by category
        for program in programs:
            cat = program.program_category or "Other"
            stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

        # Save to database
        if programs:
            save_results = self.repository.save_many(programs)
            stats["programs_saved"] = save_results.get(
                "inserted", 0
            ) + save_results.get("updated", 0)
            stats["failed"] = save_results.get("failed", 0)

            # Update university with aggregated data from all program pages
            university_names = set(
                p.university_name for p in programs if p.university_name
            )
            for uni_name in university_names:
                try:
                    await self.update_university_with_aggregated_data(uni_name)
                    logger.info(f"✓ Updated university data for: {uni_name}")
                except Exception as e:
                    logger.warning(
                        f"Failed to update university data for {uni_name}: {e}"
                    )

        logger.info(f"Comprehensive scrape completed: {stats}")
        return stats

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
            program for program in scraped_data.values() if program is not None
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

    async def _extract_and_aggregate_university_data(
        self, university_name: str, url: str, html_content: str
    ) -> None:
        """
        Extract university data from a program page and aggregate it.

        Args:
            university_name: Name of the university
            url: URL of the program page
            html_content: HTML content of the page
        """
        try:
            # Extract university-specific data from the page
            uni_data = await self.content_extractor.extract_university_data(
                url, html_content
            )

            if uni_data:
                # Initialize aggregated data for this university if not exists
                if university_name not in self._aggregated_university_data:
                    self._aggregated_university_data[university_name] = {}

                # Merge extracted data into aggregated data
                self._merge_university_data(
                    self._aggregated_university_data[university_name], uni_data
                )
                logger.debug(
                    f"Aggregated university data for {university_name} from {url}"
                )

        except Exception as e:
            logger.debug(f"Failed to extract university data from {url}: {e}")

    def _merge_university_data(
        self, aggregated: Dict[str, Any], new_data: Dict[str, Any]
    ) -> None:
        """
        Merge new university data into aggregated data.
        Prefers non-empty values and longer descriptions.

        Args:
            aggregated: Existing aggregated data (modified in place)
            new_data: New data to merge
        """
        # Fields where we want the longest/most complete value
        text_fields = ["description", "motto", "address"]

        # Fields where we take the first non-null value
        single_value_fields = [
            "website",
            "admissions_url",
            "email",
            "phone",
            "founding_year",
            "total_students",
            "international_students",
            "faculty_count",
            "student_faculty_ratio",
            "endowment_usd",
            "average_tuition_domestic",
            "average_tuition_international",
            "qs_world_ranking",
            "the_world_ranking",
            "us_news_ranking",
            "arwu_ranking",
            "type",
            "tier",
            "research_intensity",
            "libraries_count",
            "logo_url",
            "mascot",
            "latitude",
            "longitude",
            "campus_type",
            "campus_size_acres",
            "state_province",
        ]

        # List fields to be merged
        list_fields = [
            "alternate_names",
            "research_centers",
            "sports_facilities",
            "housing_options",
            "accreditations",
            "memberships",
            "student_organizations",
            "support_services",
            "international_support",
            "colors",
        ]

        # Dict fields to be merged
        dict_fields = ["subject_rankings", "social_media"]

        for field in text_fields:
            if field in new_data and new_data[field]:
                existing = aggregated.get(field, "")
                new_val = new_data[field]
                # Keep the longer/more detailed value
                if len(str(new_val)) > len(str(existing)):
                    aggregated[field] = new_val

        for field in single_value_fields:
            if field in new_data and new_data[field] is not None:
                # Only set if not already set
                if field not in aggregated or aggregated[field] is None:
                    aggregated[field] = new_data[field]

        for field in list_fields:
            if field in new_data and new_data[field]:
                existing_list = aggregated.get(field, [])
                new_items = new_data[field]
                if isinstance(new_items, str):
                    new_items = [new_items]
                # Merge unique values
                aggregated[field] = list(set(existing_list + new_items))

        for field in dict_fields:
            if field in new_data and new_data[field]:
                existing_dict = aggregated.get(field, {})
                aggregated[field] = {**existing_dict, **new_data[field]}

    async def update_university_with_aggregated_data(
        self, university_name: str
    ) -> bool:
        """
        Update university record with all aggregated data collected during scraping.

        Args:
            university_name: Name of the university to update

        Returns:
            bool: True if update was successful
        """
        if university_name not in self._aggregated_university_data:
            logger.debug(f"No aggregated data for university: {university_name}")
            return True

        aggregated_data = self._aggregated_university_data[university_name]

        if not aggregated_data:
            logger.debug(f"Empty aggregated data for university: {university_name}")
            return True

        logger.info(
            f"Updating university {university_name} with {len(aggregated_data)} aggregated fields"
        )

        success = self.university_repository.enrich_university_from_aggregated_data(
            university_name, aggregated_data
        )

        if success:
            # Clear aggregated data for this university after successful update
            del self._aggregated_university_data[university_name]
            logger.info(f"Successfully enriched university data for: {university_name}")

        return success

    def clear_aggregated_data(self, university_name: str = None) -> None:
        """
        Clear aggregated university data.

        Args:
            university_name: Specific university to clear, or None to clear all
        """
        if university_name:
            self._aggregated_university_data.pop(university_name, None)
        else:
            self._aggregated_university_data.clear()

    def get_scraper_stats(self) -> dict:
        """Get scraper statistics and configuration."""
        base_stats = self.get_scraper_info()

        # Add scraper-specific stats
        base_stats.update(
            {
                "content_extractor_cache": self.content_extractor.get_cache_stats(),
                "repository_connected": True,  # Could add actual connection check
                "aggregated_universities": len(self._aggregated_university_data),
            }
        )

        return base_stats
