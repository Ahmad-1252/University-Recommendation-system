"""LLM service for Groq API integration."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from groq import Groq
import hashlib
import json

from ..core.config import get_settings
from ..core.exceptions import GroqAPIError, RateLimitError
from ..core.constants import LLM_PROMPTS

logger = logging.getLogger(__name__)


class LLMService:
    """Service for handling Groq LLM API interactions."""

    def __init__(self):
        self.settings = get_settings()
        self.client = Groq(api_key=self.settings.llm.api_key)
        self.model = self.settings.llm.model
        self.timeout = self.settings.llm.timeout
        self.max_retries = self.settings.llm.max_retries
        self.temperature = self.settings.llm.temperature
        self.rate_limit_delay = 1.0  # Default rate limit delay

        # Response cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_enabled = True

    def enable_cache(self) -> None:
        """Enable response caching."""
        self._cache_enabled = True
        logger.info("LLM response caching enabled")

    def disable_cache(self) -> None:
        """Disable response caching."""
        self._cache_enabled = False
        logger.info("LLM response caching disabled")

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
        logger.info("LLM response cache cleared")

    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """Generate cache key from prompt and parameters."""
        key_data = {
            "prompt": prompt,
            "model": self.model,
            **kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def generate_completion(self,
                                prompt: str,
                                temperature: float = 0.1,
                                max_tokens: Optional[int] = None,
                                **kwargs) -> str:
        """
        Generate a completion using the Groq API.

        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated text response

        Raises:
            GroqAPIError: If API call fails
            RateLimitError: If rate limit is exceeded
        """
        # Check cache first
        cache_key = self._get_cache_key(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)

        if self._cache_enabled and cache_key in self._cache:
            cached_response = self._cache[cache_key]
            logger.debug("Using cached LLM response")
            return cached_response["response"]

        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Remove None values
        api_params = {k: v for k, v in api_params.items() if v is not None}

        # Add any additional kwargs
        api_params.update(kwargs)

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Making LLM API call (attempt {attempt + 1})")

                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(**api_params)
                )

                generated_text = response.choices[0].message.content

                # Cache the response
                if self._cache_enabled:
                    self._cache[cache_key] = {
                        "response": generated_text,
                        "timestamp": asyncio.get_event_loop().time()
                    }

                # Rate limiting delay
                await asyncio.sleep(self.rate_limit_delay)

                return generated_text

            except Exception as e:
                error_msg = str(e).lower()

                if "rate limit" in error_msg:
                    if attempt < self.max_retries:
                        delay = (2 ** attempt) * 2  # Exponential backoff
                        logger.warning(f"Rate limit hit, retrying in {delay}s")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise RateLimitError("Rate limit exceeded, max retries reached") from e

                if attempt == self.max_retries:
                    logger.error(f"LLM API call failed after {self.max_retries + 1} attempts: {e}")
                    raise GroqAPIError(f"LLM API call failed: {e}") from e

                # Exponential backoff for other errors
                delay = 2 ** attempt
                logger.warning(f"LLM API call failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)

    async def extract_structured_data(self,
                                    content: str,
                                    schema: Dict[str, Any],
                                    prompt_template: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract structured data from content using LLM.

        Args:
            content: Text content to extract from
            schema: Expected data schema
            prompt_template: Custom prompt template

        Returns:
            Extracted structured data
        """
        if prompt_template is None:
            prompt_template = LLM_PROMPTS["program_extraction"]

        # Format the prompt with content and schema
        prompt = prompt_template.format(
            content=content,
            schema=json.dumps(schema, indent=2)
        )

        try:
            response = await self.generate_completion(
                prompt=prompt,
                temperature=0.0,  # Low temperature for extraction tasks
                max_tokens=2000
            )

            # Try to parse JSON response
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                logger.warning("LLM response is not valid JSON, attempting to extract JSON from text")
                # Try to extract JSON from the response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
                else:
                    raise ValueError("No JSON found in LLM response")

        except Exception as e:
            logger.error(f"Structured data extraction failed: {e}")
            raise GroqAPIError(f"Data extraction failed: {e}") from e

    async def validate_data_quality(self,
                                  data: Dict[str, Any],
                                  criteria: List[str]) -> Dict[str, Any]:
        """
        Validate data quality using LLM.

        Args:
            data: Data to validate
            criteria: List of validation criteria

        Returns:
            Validation results
        """
        prompt = f"""
        Validate the quality of this university program data:

        Data: {json.dumps(data, indent=2)}

        Validation Criteria:
        {chr(10).join(f"- {criterion}" for criterion in criteria)}

        Provide a JSON response with:
        - overall_score: 0-1 quality score
        - criteria_scores: object with scores for each criterion
        - issues: array of identified issues
        - recommendations: array of improvement suggestions
        """

        try:
            response = await self.generate_completion(
                prompt=prompt,
                temperature=0.0,
                max_tokens=1000
            )

            return json.loads(response)

        except Exception as e:
            logger.error(f"Data quality validation failed: {e}")
            return {
                "overall_score": 0.0,
                "criteria_scores": {},
                "issues": [str(e)],
                "recommendations": ["Manual review required"]
            }

    async def generate_summary(self,
                             content: str,
                             max_length: int = 300) -> str:
        """
        Generate a summary of content using LLM.

        Args:
            content: Content to summarize
            max_length: Maximum summary length

        Returns:
            Generated summary
        """
        prompt = f"""
        Summarize the following university program information in {max_length} characters or less.
        Focus on key academic requirements, program features, and outcomes:

        {content}
        """

        try:
            return await self.generate_completion(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500
            )

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return f"Summary unavailable: {str(e)}"

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "model": self.model,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "rate_limit_delay": self.rate_limit_delay,
            "cache_enabled": self._cache_enabled,
            "cache_size": len(self._cache)
        }