"""University Recommendation System - A comprehensive AI-powered university program scraper and analyzer."""

__version__ = "1.0.0"
__author__ = "University Recommendation System Team"
__description__ = "AI-powered system for scraping and analyzing computer science programs from global universities"

# Import main components for easy access
from .core import Settings, get_settings

__all__ = ["get_settings", "Settings", "__version__", "__author__", "__description__"]
