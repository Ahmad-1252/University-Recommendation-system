"""Link discovery logic for finding university program pages."""

import asyncio
import logging
from typing import List, Set, Optional
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler

from ..core.config import get_settings
from ..core.exceptions import ScrapingError

logger = logging.getLogger(__name__)


class LinkDiscoverer:
    """Discovers relevant links from university websites."""

    def __init__(self):
        self.settings = get_settings()
        self.timeout = self.settings.scraping.timeout

        # Keywords that indicate program pages
        self.program_keywords = {
            "computer science", "cs", "computing", "informatics",
            "software engineering", "data science", "ai", "artificial intelligence",
            "machine learning", "cybersecurity", "information technology",
            "masters", "msc", "ms", "phd", "doctorate", "bachelor", "undergraduate"
        }

        # URL patterns to avoid
        self.exclude_patterns = {
            "facebook.com", "twitter.com", "linkedin.com", "instagram.com",
            "youtube.com", "calendar", "events", "news", "blog", "contact",
            "about", "staff", "faculty", "alumni", "login", "register"
        }

    async def discover_program_links(self,
                                   base_url: str,
                                   max_pages: int = 10,
                                   max_depth: int = 2) -> List[str]:
        """
        Discover program-related links from a university website.

        Args:
            base_url: Base URL of the university website
            max_pages: Maximum number of pages to crawl
            max_depth: Maximum crawl depth

        Returns:
            List of discovered program URLs
        """
        logger.info(f"Starting link discovery from {base_url}")

        discovered_links: Set[str] = set()
        visited_urls: Set[str] = set()

        async with AsyncWebCrawler() as crawler:
            await self._crawl_recursive(
                crawler, base_url, discovered_links, visited_urls,
                max_pages, max_depth, current_depth=0
            )

        program_links = list(discovered_links)
        logger.info(f"Discovered {len(program_links)} program links")
        return program_links

    async def _crawl_recursive(self,
                             crawler: AsyncWebCrawler,
                             url: str,
                             discovered_links: Set[str],
                             visited_urls: Set[str],
                             max_pages: int,
                             max_depth: int,
                             current_depth: int) -> None:
        """Recursively crawl pages to discover links."""

        if current_depth > max_depth or len(visited_urls) >= max_pages:
            return

        if url in visited_urls:
            return

        visited_urls.add(url)

        try:
            # Crawl the page
            result = await crawler.arun(url=url, timeout=self.timeout)

            if not result.success:
                logger.warning(f"Failed to crawl {url}")
                return

            # Extract links from the page
            soup = result.soup
            if not soup:
                return

            links = soup.find_all('a', href=True)
            page_links = []

            for link in links:
                href = link.get('href')
                if href:
                    absolute_url = urljoin(url, href)
                    if self._is_relevant_link(absolute_url, url):
                        page_links.append(absolute_url)

            # Filter for program links
            for link_url in page_links:
                if self._is_program_page(link_url):
                    discovered_links.add(link_url)

            # Recursively crawl relevant internal links
            internal_links = [link for link in page_links[:5] if self._is_internal_link(link, url)]

            for internal_link in internal_links:
                await self._crawl_recursive(
                    crawler, internal_link, discovered_links, visited_urls,
                    max_pages, max_depth, current_depth + 1
                )

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")

    def _is_relevant_link(self, url: str, base_url: str) -> bool:
        """Check if a link is relevant for crawling."""
        try:
            parsed = urlparse(url)

            # Skip non-HTTP URLs
            if parsed.scheme not in ['http', 'https']:
                return False

            # Skip external links (unless they're university subdomains)
            if not self._is_internal_link(url, base_url):
                return False

            # Skip excluded patterns
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in self.exclude_patterns):
                return False

            # Skip file downloads
            if any(url_lower.endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                return False

            return True

        except Exception:
            return False

    def _is_internal_link(self, url: str, base_url: str) -> bool:
        """Check if a link is internal to the university website."""
        try:
            base_domain = urlparse(base_url).netloc
            link_domain = urlparse(url).netloc

            # Allow subdomains of the base domain
            return link_domain.endswith(base_domain) or base_domain.endswith(link_domain)

        except Exception:
            return False

    def _is_program_page(self, url: str) -> bool:
        """Check if a URL likely contains program information."""
        url_lower = url.lower()

        # Check for program-related keywords in URL
        keyword_matches = sum(1 for keyword in self.program_keywords if keyword in url_lower)

        # Check for common program page patterns
        pattern_matches = 0
        program_patterns = [
            "/program", "/course", "/study", "/degree", "/masters", "/phd",
            "/undergraduate", "/graduate", "/academic", "/admission"
        ]

        for pattern in program_patterns:
            if pattern in url_lower:
                pattern_matches += 1

        # Consider it a program page if it has multiple keyword matches or pattern matches
        return keyword_matches >= 2 or pattern_matches >= 1

    async def validate_program_urls(self, urls: List[str]) -> List[str]:
        """
        Validate that URLs are accessible and contain program information.

        Args:
            urls: List of URLs to validate

        Returns:
            List of valid program URLs
        """
        logger.info(f"Validating {len(urls)} program URLs")

        valid_urls = []

        async with AsyncWebCrawler() as crawler:
            # Process in batches to avoid overwhelming the server
            batch_size = 5

            for i in range(0, len(urls), batch_size):
                batch = urls[i:i + batch_size]

                tasks = []
                for url in batch:
                    tasks.append(self._validate_single_url(crawler, url))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.warning(f"Validation failed for {url}: {result}")
                    elif result:
                        valid_urls.append(url)

                # Rate limiting
                await asyncio.sleep(1)

        logger.info(f"Validated {len(valid_urls)} out of {len(urls)} URLs")
        return valid_urls

    async def _validate_single_url(self, crawler: AsyncWebCrawler, url: str) -> bool:
        """Validate a single URL."""
        try:
            result = await crawler.arun(
                url=url,
                timeout=self.timeout,
                only_text=True  # We only need text content for validation
            )

            if not result.success:
                return False

            content = result.markdown or ""
            content_lower = content.lower()

            # Check if content contains program-related keywords
            program_indicators = [
                "computer science", "masters", "bachelor", "phd",
                "admission requirements", "tuition", "application deadline"
            ]

            matches = sum(1 for indicator in program_indicators if indicator in content_lower)

            return matches >= 2

        except Exception as e:
            logger.debug(f"URL validation error for {url}: {e}")
            return False