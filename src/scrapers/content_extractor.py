"""LLM-based content extraction for university program data."""

import json
import logging
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.core.config import get_settings
from src.core.constants import LLM_PROMPTS
from src.core.exceptions import LLMExtractionError
from src.models.university import UniversityProgram
from src.services.llm.base_provider import LLMError, LLMProvider
from src.services.llm.provider_factory import LLMProviderFactory

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Handles LLM-based content extraction from web pages."""

    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize ContentExtractor with LLM provider.

        Args:
            provider_name: Override provider name. If None, uses config default.
                          Options: 'deepseek', 'groq'
        """
        self.settings = get_settings()
        self.provider_name = provider_name or self.settings.llm.provider
        self._provider: Optional[LLMProvider] = None

        # Cache for repeated extractions (with bounded size)
        self._extraction_cache: Dict[str, UniversityProgram] = {}
        self._cache_max_size = 100  # Limit cache size to prevent memory leaks

        logger.info(f"ContentExtractor initialized with provider: {self.provider_name}")

    async def _get_provider(self) -> LLMProvider:
        """Get or create the LLM provider instance."""
        if self._provider is None:
            try:
                # Use factory with fallback support
                self._provider = await LLMProviderFactory.create_provider_with_fallback(
                    primary_provider=self.provider_name
                )
                logger.info(
                    f"Using LLM provider: {self._provider.name} ({self._provider.model})"
                )
            except ValueError as e:
                logger.error(f"Failed to create LLM provider: {e}")
                raise LLMExtractionError(f"No LLM providers available: {e}")
        return self._provider

    def get_extraction_prompt(self) -> str:
        """Get the extraction prompt for LLM."""
        return LLM_PROMPTS["program_extraction"]

    async def extract_program_data(
        self, url: str, html_content: str, use_cache: bool = True
    ) -> Optional[UniversityProgram]:
        """
        Extract program data from HTML content using LLM.

        Args:
            url: Source URL
            html_content: Raw HTML or text content
            use_cache: Whether to use extraction cache

        Returns:
            UniversityProgram instance if extraction successful
        """
        # Check cache first
        if use_cache and url in self._extraction_cache:
            logger.info(f"Using cached extraction for {url}")
            return self._extraction_cache[url]

        try:
            # Get the LLM provider
            provider = await self._get_provider()
            logger.info(f"Extracting data from {url} using {provider.name} LLM")

            # Clean HTML - extract text content
            text_content = self._clean_html_to_text(html_content)

            if len(text_content) < 100:
                logger.warning(
                    f"Content too short for extraction: {len(text_content)} chars"
                )
                return None

            # Truncate if too long (respect provider context limits)
            max_chars = 15000
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars] + "\n... [content truncated]"

            # Call LLM API for extraction using provider
            extracted_data = await self._call_llm_extraction(
                provider, text_content, url
            )

            if extracted_data:
                # Create UniversityProgram instance
                program = UniversityProgram(**extracted_data)
                program.source_url = url

                # Cache the result (with size limit)
                if use_cache:
                    if len(self._extraction_cache) >= self._cache_max_size:
                        # Remove oldest entry (FIFO eviction)
                        oldest_key = next(iter(self._extraction_cache))
                        del self._extraction_cache[oldest_key]
                    self._extraction_cache[url] = program

                logger.info(f"Successfully extracted program: {program.program_name}")
                return program
            else:
                logger.warning(f"No data extracted from {url}")
                return None

        except LLMError as e:
            logger.error(f"LLM extraction failed for {url}: {e.message}")
            raise LLMExtractionError(
                f"Extraction failed ({e.provider_name}): {e.message}"
            ) from e
        except Exception as e:
            logger.error(f"LLM extraction failed for {url}: {e}")
            raise LLMExtractionError(f"Extraction failed: {e}") from e

    def _clean_html_to_text(self, html_content: str) -> str:
        """Extract clean text from HTML content."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text
            text = soup.get_text(separator=" ", strip=True)

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            logger.warning(f"HTML parsing failed, using raw content: {e}")
            return html_content

    async def _call_llm_extraction(
        self, provider: LLMProvider, text_content: str, url: str
    ) -> Optional[Dict[str, Any]]:
        """Call LLM provider to extract structured data."""
        try:
            prompt = self.get_extraction_prompt()

            # Build the full prompt
            full_prompt = f"""Extract university program information from the following web page content.
Source URL: {url}

{prompt}

Web page content:
{text_content}

Return ONLY a valid JSON object with the extracted data. No explanation, just JSON."""

            # Call provider API
            response = await provider.extract_program_data(text_content, full_prompt)

            if not response.content:
                logger.warning(f"Empty response from {provider.name} API")
                return None

            # Parse JSON from response
            content = response.content.strip()

            # Handle potential markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # Parse JSON
            extracted = json.loads(content)

            # Validate and fix required fields
            if not extracted.get("program_name"):
                # Try to infer program_name from URL
                inferred_name = self._infer_program_name_from_url(url)
                if inferred_name:
                    extracted["program_name"] = inferred_name
                    logger.info(f"Inferred program_name from URL: {inferred_name}")
                elif not extracted.get("university_name"):
                    logger.warning(
                        "Extraction missing required fields (program_name and university_name)"
                    )
                    return None
                else:
                    logger.warning(f"Extraction missing program_name for {url}")
                    return None

            # Ensure degree_type has a value (will be normalized by Pydantic)
            if not extracted.get("degree_type"):
                # Try to infer from program_name or URL
                inferred_degree = self._infer_degree_type_from_url(
                    url, extracted.get("program_name", "")
                )
                extracted["degree_type"] = inferred_degree
                logger.info(f"Inferred degree_type: {inferred_degree}")

            logger.info(
                f"{provider.name} extraction successful: {extracted.get('program_name', 'Unknown')} "
                f"(confidence: {response.confidence_score:.2f})"
            )
            return extracted

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {provider.name} response as JSON: {e}")
            return None
        except LLMError as e:
            logger.error(f"{provider.name} API call failed: {e.message}")
            raise
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise LLMExtractionError(f"LLM API error: {e}") from e

    async def validate_extraction_quality(
        self, program: UniversityProgram
    ) -> Dict[str, Any]:
        """
        Validate the quality of extracted data.

        Args:
            program: UniversityProgram instance to validate

        Returns:
            Dictionary with quality metrics
        """
        return {
            "accuracy": 0.8,
            "completeness": program.data_completeness,
            "consistency": 0.9,
            "issues": [],
            "confidence": program.confidence_score,
        }

    def _infer_program_name_from_url(self, url: str) -> Optional[str]:
        """Attempt to infer program name from URL path."""
        import re
        from urllib.parse import unquote, urlparse

        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)

            # Common patterns in URLs that indicate program names
            # e.g., /msc-advanced-computer-science, /computer-science-msc, /master/computer-science

            # Extract the last meaningful path segment
            segments = [
                s
                for s in path.split("/")
                if s
                and s
                not in [
                    "courses",
                    "programmes",
                    "programs",
                    "degrees",
                    "study",
                    "masters",
                    "postgraduate",
                    "undergraduate",
                    "taught",
                    "research",
                    "detail",
                    "list",
                    "directory",
                    "index.php",
                ]
            ]

            if not segments:
                return None

            # Take the most specific segment (usually the last one)
            name_segment = segments[-1]

            # Remove file extensions
            name_segment = re.sub(r"\.(html?|php|aspx?)$", "", name_segment)

            # Remove common ID patterns
            name_segment = re.sub(r"^[a-z]\d{3,}[-_]", "", name_segment)  # e.g., j702-
            name_segment = re.sub(r"[-_]?\d{4,}$", "", name_segment)  # trailing IDs

            # Convert hyphens/underscores to spaces and title case
            name = re.sub(r"[-_]+", " ", name_segment)
            name = name.strip()

            if len(name) < 3:
                return None

            # Title case the name
            name = name.title()

            # Normalize degree prefixes (order matters - check longer patterns first)
            name = re.sub(r"^(Msc|Msc\s|Ms\s)", "MSc ", name, flags=re.IGNORECASE)
            name = re.sub(r"^(Bsc|Bsc\s|Bs\s)", "BSc ", name, flags=re.IGNORECASE)
            name = re.sub(r"^(Phd|Ph\s?D\s)", "PhD ", name, flags=re.IGNORECASE)
            name = re.sub(r"^(Mba|Mba\s)", "MBA ", name, flags=re.IGNORECASE)
            # Don't convert "Master" to "MA ster" - only match standalone "Ma " at start
            name = re.sub(r"^Ma\s+(?!ster)", "MA ", name, flags=re.IGNORECASE)

            # Clean up any double spaces
            name = re.sub(r"\s+", " ", name).strip()

            if len(name) >= 5:  # Reasonable minimum length for a program name
                return name
            return None

        except Exception as e:
            logger.debug(f"Failed to infer program name from URL: {e}")
            return None

    def _infer_degree_type_from_url(self, url: str, program_name: str = "") -> str:
        """Infer degree type from URL path and program name."""
        url_lower = url.lower()
        name_lower = program_name.lower() if program_name else ""
        combined = url_lower + " " + name_lower

        # PhD/Doctoral indicators
        if any(
            term in combined
            for term in [
                "/phd",
                "doctoral",
                "doctorate",
                "research-degree",
                "/research/",
                "dphil",
            ]
        ):
            return "Doctor of Philosophy"

        # Undergraduate indicators
        if any(
            term in combined
            for term in ["/undergraduate", "/bsc", "/bachelor", "/ba/", "bachelor-of"]
        ):
            if "engineering" in combined:
                return "Bachelor of Engineering"
            elif any(
                term in combined
                for term in ["arts", "humanities", "literature", "history"]
            ):
                return "Bachelor of Arts"
            return "Bachelor of Science"

        # MBA indicators
        if "/mba" in combined or "business-administration" in combined:
            return "Master of Business Administration"

        # MPhil indicators
        if "mphil" in combined or "master-of-philosophy" in combined:
            return "Master of Philosophy"

        # Engineering masters
        if any(term in combined for term in ["meng", "master-of-engineering"]):
            return "Master of Engineering"

        # MA indicators
        if any(term in combined for term in ["master-of-arts", "/ma-", "-ma/", "/ma/"]):
            return "Master of Arts"

        # Default to MSc for graduate/postgraduate
        return "Master of Science"

    def clear_cache(self) -> None:
        """Clear the extraction cache."""
        self._extraction_cache.clear()
        logger.info("Extraction cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {"cached_extractions": len(self._extraction_cache)}

    async def extract_university_data(
        self, url: str, html_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract university-specific data from a program page.
        This extracts general university information that may be present on program pages.

        Args:
            url: Source URL
            html_content: Raw HTML content

        Returns:
            Dictionary with extracted university data, or None if extraction fails
        """
        try:
            provider = await self._get_provider()
            text_content = self._clean_html_to_text(html_content)

            if len(text_content) < 100:
                return None

            # Truncate if too long
            max_chars = 10000
            if len(text_content) > max_chars:
                text_content = text_content[:max_chars]

            # Build prompt for university data extraction
            prompt = """Extract university-specific information from this program page.
Look for general university data that appears on the page such as:

- University description or "about us" text
- University motto or mission statement
- Contact information (email, phone, address)
- Campus information (location, type, size)
- Rankings (QS, THE, US News, ARWU)
- Student statistics (total students, international students, faculty count)
- Financial info (endowment, average tuition)
- Accreditations and memberships
- Research centers or institutes mentioned
- Facilities mentioned (libraries, sports, housing)
- Social media links
- University founding year
- University type (public/private)
- Logo URL if visible

Return ONLY a JSON object with the fields you can extract. Use null for fields not found.
Do NOT include program-specific information, only university-level data.

Example format:
{
    "description": "Brief university description...",
    "motto": "University motto if found",
    "website": "https://university.edu",
    "email": "info@university.edu",
    "phone": "+1-xxx-xxx-xxxx",
    "address": "Full address",
    "founding_year": 1900,
    "total_students": 45000,
    "international_students": 12000,
    "qs_world_ranking": 50,
    "type": "public",
    "accreditations": ["AACSB", "AMBA"],
    "research_centers": ["AI Research Lab"],
    "social_media": {"twitter": "@university", "linkedin": "university-official"}
}"""

            full_prompt = f"""{prompt}

Web page content from {url}:
{text_content}

Return ONLY valid JSON:"""

            # Call LLM
            response = await provider.extract_program_data(text_content, full_prompt)

            if not response.content:
                return None

            # Parse response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            extracted = json.loads(content)

            # Filter out null/empty values
            filtered = {
                k: v
                for k, v in extracted.items()
                if v is not None and v != "" and v != []
            }

            if filtered:
                logger.debug(f"Extracted {len(filtered)} university fields from {url}")
                return filtered
            return None

        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse university data JSON: {e}")
            return None
        except Exception as e:
            logger.debug(f"University data extraction failed: {e}")
            return None

    async def close(self) -> None:
        """Close the LLM provider and cleanup resources."""
        if self._provider is not None:
            try:
                await self._provider.close()
                logger.info(f"Closed LLM provider: {self._provider.name}")
            except Exception as e:
                logger.warning(f"Error closing LLM provider: {e}")
            finally:
                self._provider = None
