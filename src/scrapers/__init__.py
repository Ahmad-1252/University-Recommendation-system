"""Scraping modules for the University Recommendation System."""

from .base_scraper import BaseScraper
from .university_scraper import UniversityScraper
from .content_extractor import ContentExtractor
from .link_discoverer import LinkDiscoverer

__all__ = [
    "BaseScraper",
    "UniversityScraper",
    "ContentExtractor",
    "LinkDiscoverer"
]