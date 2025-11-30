"""Scraping modules for the University Recommendation System."""

from scrapers.base_scraper import BaseScraper
from scrapers.university_scraper import UniversityScraper
from scrapers.content_extractor import ContentExtractor
from scrapers.link_discoverer import LinkDiscoverer

__all__ = [
    "BaseScraper",
    "UniversityScraper",
    "ContentExtractor",
    "LinkDiscoverer"
]