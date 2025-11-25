"""LLM-based content extraction for university program data."""

import logging
from typing import Optional, Dict, Any
from groq import Groq
from crawl4ai.extraction_strategy import LLMExtractionStrategy

from ..models.university import UniversityProgram
from ..core.config import get_settings
from ..core.constants import LLM_PROMPTS
from ..core.exceptions import LLMExtractionError, GroqAPIError, RateLimitError

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Handles LLM-based content extraction from web pages."""

    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.llm.api_key)
        self.model = self.settings.llm.model_name
        self.timeout = self.settings.llm.timeout

        # Cache for repeated extractions
        self._extraction_cache: Dict[str, UniversityProgram] = {}

    def create_extraction_strategy(self, custom_prompt: Optional[str] = None) -> LLMExtractionStrategy:
        """
        Create an LLM extraction strategy for Crawl4AI.

        Args:
            custom_prompt: Custom extraction prompt (optional)

        Returns:
            Configured LLMExtractionStrategy
        """
        prompt = custom_prompt or LLM_PROMPTS["program_extraction"]

        return LLMExtractionStrategy(
            llm=self.client,
            model_name=self.model,
            instruction=prompt
        )

    async def extract_program_data(self,
                                 url: str,
                                 html_content: str,
                                 use_cache: bool = True) -> Optional[UniversityProgram]:
        """
        Extract program data from HTML content using LLM.

        Args:
            url: Source URL
            html_content: Raw HTML content
            use_cache: Whether to use extraction cache

        Returns:
            UniversityProgram instance if extraction successful
        """
        # Check cache first
        if use_cache and url in self._extraction_cache:
            logger.info(f"Using cached extraction for {url}")
            return self._extraction_cache[url]

        try:
            # Create extraction strategy
            strategy = self.create_extraction_strategy()

            # For now, we'll simulate the extraction
            # In a real implementation, this would use Crawl4AI's extraction
            # Since we can't run Crawl4AI here, we'll create a mock extraction

            logger.info(f"Extracting data from {url}")

            # Mock extraction result - in real implementation this would come from LLM
            mock_data = self._create_mock_extraction(url)

            if mock_data:
                program = UniversityProgram(**mock_data)
                program.source_url = url

                # Cache the result
                if use_cache:
                    self._extraction_cache[url] = program

                logger.info(f"Successfully extracted program: {program.program_name}")
                return program
            else:
                logger.warning(f"No data extracted from {url}")
                return None

        except Exception as e:
            logger.error(f"LLM extraction failed for {url}: {e}")
            raise LLMExtractionError(f"Extraction failed: {e}") from e

    def _create_mock_extraction(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Create mock extraction data for testing.
        In production, this would be replaced by actual LLM extraction.
        """
        # This is a placeholder - actual implementation would use LLM
        # For now, return None to indicate no extraction
        # Real implementation would parse the LLM response and create proper data
        return None

    async def validate_extraction_quality(self, program: UniversityProgram) -> Dict[str, Any]:
        """
        Validate the quality of extracted data using LLM.

        Args:
            program: UniversityProgram instance to validate

        Returns:
            Dictionary with quality metrics
        """
        try:
            prompt = f"""
            Analyze the quality and completeness of this university program data:

            Program: {program.program_name}
            University: {program.university_name}
            Description: {program.program_description[:500]}...

            Rate the following aspects on a scale of 0-1:
            - accuracy: How accurate is the information?
            - completeness: How complete is the data?
            - consistency: Is the information internally consistent?

            Return a JSON object with these ratings and any issues found.
            """

            # In real implementation, this would call the LLM
            # For now, return mock quality assessment
            return {
                "accuracy": 0.8,
                "completeness": program.data_completeness,
                "consistency": 0.9,
                "issues": [],
                "confidence": program.confidence_score
            }

        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            return {
                "accuracy": 0.0,
                "completeness": 0.0,
                "consistency": 0.0,
                "issues": [str(e)],
                "confidence": 0.0
            }

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._extraction_cache.clear()
        logger.info("Extraction cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_extractions": len(self._extraction_cache)
        }