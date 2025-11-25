"""Validation and quality assurance services."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import re
from crawl4ai import AsyncWebCrawler

from ..core.config import get_settings
from ..core.exceptions import ValidationError
from ..models.university import UniversityProgram

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating URLs, data quality, and content."""

    def __init__(self):
        self.settings = get_settings()
        self.timeout = self.settings.scraping.timeout

        # URL validation patterns
        self.university_domains = {
            ".edu", ".ac.uk", ".ac.au", ".ac.nz", ".ac.ca",
            ".edu.au", ".edu.sg", ".edu.hk", ".edu.cn"
        }

        # Content validation patterns
        self.program_keywords = [
            "computer science", "masters", "bachelor", "phd",
            "admission", "tuition", "requirements", "application"
        ]

    async def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate if a URL is accessible and contains university program content.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, reason)
        """
        try:
            # Basic URL structure validation
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "Invalid URL structure"

            # Domain validation
            if not self._is_university_domain(parsed.netloc):
                return False, "Not a recognized university domain"

            # Accessibility check
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=url,
                    timeout=self.timeout,
                    only_text=True
                )

                if not result.success:
                    return False, f"URL not accessible: {result.error_message}"

                # Content validation
                content = result.markdown or ""
                if not self._validate_content_relevance(content):
                    return False, "Content does not appear to be program information"

                return True, "Valid university program URL"

        except Exception as e:
            logger.error(f"URL validation error for {url}: {e}")
            return False, f"Validation error: {str(e)}"

    async def validate_urls_batch(self, urls: List[str]) -> Dict[str, Tuple[bool, str]]:
        """
        Validate multiple URLs concurrently.

        Args:
            urls: List of URLs to validate

        Returns:
            Dictionary mapping URLs to (is_valid, reason) tuples
        """
        logger.info(f"Validating {len(urls)} URLs")

        # Limit concurrent requests
        semaphore = asyncio.Semaphore(5)

        async def validate_with_semaphore(url: str) -> Tuple[str, Tuple[bool, str]]:
            async with semaphore:
                result = await self.validate_url(url)
                return url, result

        tasks = [validate_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        validation_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch validation task failed: {result}")
                continue

            url, (is_valid, reason) = result
            validation_results[url] = (is_valid, reason)

        return validation_results

    def _is_university_domain(self, domain: str) -> bool:
        """Check if domain appears to be a university domain."""
        domain_lower = domain.lower()

        # Check for university TLDs
        if any(domain_lower.endswith(tld) for tld in self.university_domains):
            return True

        # Check for university keywords in domain
        university_keywords = ["university", "college", "institute", "school"]
        return any(keyword in domain_lower for keyword in university_keywords)

    def _validate_content_relevance(self, content: str) -> bool:
        """Validate if content is relevant to university programs."""
        if not content:
            return False

        content_lower = content.lower()

        # Count relevant keywords
        keyword_count = sum(
            1 for keyword in self.program_keywords
            if keyword in content_lower
        )

        # Check for minimum relevance threshold
        return keyword_count >= 2

    def validate_program_data(self, program: UniversityProgram) -> Dict[str, Any]:
        """
        Validate the quality and completeness of program data.

        Args:
            program: UniversityProgram instance to validate

        Returns:
            Validation results dictionary
        """
        issues = []
        warnings = []
        score = 0.0
        max_score = 0.0

        # Required fields validation
        required_fields = [
            ("university_name", "University name is required"),
            ("program_name", "Program name is required"),
            ("degree_type", "Degree type is required"),
            ("country", "Country is required"),
            ("source_url", "Source URL is required")
        ]

        for field, error_msg in required_fields:
            max_score += 1
            value = getattr(program, field, None)
            if not value or str(value).strip() == "":
                issues.append(error_msg)
            else:
                score += 1

        # Field format validation
        max_score += 1
        if program.gpa_requirement_min is not None:
            if not (0 <= program.gpa_requirement_min <= 4.0):
                issues.append("GPA requirement must be between 0.0 and 4.0")
            else:
                score += 0.5

        # Language requirements validation
        lang_req = program.language_requirements
        if lang_req.toefl_min and not (0 <= lang_req.toefl_min <= 120):
            issues.append("TOEFL score must be between 0 and 120")
        if lang_req.ielts_min and not (0 <= lang_req.ielts_min <= 9.0):
            issues.append("IELTS score must be between 0.0 and 9.0")

        # URL validation
        max_score += 1
        try:
            parsed = urlparse(program.source_url)
            if parsed.scheme not in ['http', 'https']:
                issues.append("Source URL must use HTTP or HTTPS")
            else:
                score += 1
        except Exception:
            issues.append("Invalid source URL format")

        # Content quality checks
        if program.program_description and len(program.program_description) < 50:
            warnings.append("Program description seems too short")

        if program.tuition_fees.international_per_year and program.tuition_fees.international_per_year < 1000:
            warnings.append("Tuition fee seems unusually low")

        # Calculate final score
        final_score = score / max_score if max_score > 0 else 0.0

        return {
            "is_valid": len(issues) == 0,
            "score": final_score,
            "issues": issues,
            "warnings": warnings,
            "recommendations": self._generate_recommendations(issues, warnings)
        }

    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """Generate recommendations based on validation issues."""
        recommendations = []

        if any("required" in issue.lower() for issue in issues):
            recommendations.append("Complete all required fields before saving")

        if any("url" in issue.lower() for issue in issues):
            recommendations.append("Verify source URL is correct and accessible")

        if any("gpa" in issue.lower() for issue in issues):
            recommendations.append("Ensure GPA requirements are in 4.0 scale format")

        if warnings:
            recommendations.append("Review warnings for potential data quality issues")

        return recommendations

    async def check_url_freshness(self, url: str, last_checked: Optional[float] = None) -> Dict[str, Any]:
        """
        Check if a URL content has changed since last check.

        Args:
            url: URL to check
            last_checked: Timestamp of last check

        Returns:
            Freshness check results
        """
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=url,
                    timeout=self.timeout,
                    only_text=True
                )

                if not result.success:
                    return {
                        "is_fresh": False,
                        "error": result.error_message,
                        "needs_update": True
                    }

                # In a real implementation, you'd compare content hashes
                # For now, just check if accessible
                return {
                    "is_fresh": True,
                    "last_checked": asyncio.get_event_loop().time(),
                    "needs_update": False
                }

        except Exception as e:
            return {
                "is_fresh": False,
                "error": str(e),
                "needs_update": True
            }