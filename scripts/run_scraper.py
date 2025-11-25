#!/usr/bin/env python3
"""Main entry point for scraping university program data."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import get_settings
from src.core.constants import UNIVERSITY_URLS
from src.scrapers.university_scraper import UniversityScraper
from src.cli.dashboard import Dashboard

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/scraper.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main scraping function."""
    settings = get_settings()

    logger.info("Starting University Recommendation System Scraper")
    logger.info(f"Target URLs: {len(UNIVERSITY_URLS)}")

    # Initialize scraper
    scraper = UniversityScraper()

    # Get URLs to scrape
    urls = list(UNIVERSITY_URLS.values())

    try:
        # Scrape and save all URLs
        logger.info(f"Beginning scrape of {len(urls)} university programs")

        results = await scraper.scrape_multiple_and_save(urls)

        # Report results
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful

        logger.info(f"Scraping completed: {successful} successful, {failed} failed")

        if failed > 0:
            logger.warning("Failed URLs:")
            for url, success in results.items():
                if not success:
                    logger.warning(f"  - {url}")

        # Show dashboard if successful
        if successful > 0:
            console = Dashboard()
            console.show_data_overview()

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())