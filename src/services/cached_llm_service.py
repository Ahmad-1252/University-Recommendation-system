"""Cached LLM service with Redis/memory caching."""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from ..core.config import get_settings
from .cache import Cache, CacheFactory
from .llm_service import LLMService

logger = logging.getLogger(__name__)


class CachedLLMService(LLMService):
    """LLM service with integrated caching for improved performance."""

    def __init__(self, provider=None, cache: Optional[Cache] = None):
        super().__init__(provider)

        # Initialize cache
        self.cache = cache or CacheFactory.create_cache()
        self.cache_enabled = True
        self.default_ttl = get_settings().redis.ttl

        # Cache namespaces
        self.namespaces = {
            "completions": "llm:completions",
            "extractions": "llm:extractions",
            "validations": "llm:validations",
            "summaries": "llm:summaries",
        }

    async def enable_cache(self) -> None:
        """Enable response caching."""
        self.cache_enabled = True
        logger.info("LLM caching enabled")

    async def disable_cache(self) -> None:
        """Disable response caching."""
        self.cache_enabled = False
        logger.info("LLM caching disabled")

    async def clear_cache(self) -> None:
        """Clear the LLM response cache."""
        await self.cache.clear(self.namespaces["completions"])
        logger.info("LLM response cache cleared")

    def _make_cache_key(self, content: str, prompt: str, **kwargs) -> str:
        """Generate a deterministic cache key from inputs."""
        # Create a hash of the content and prompt
        key_data = {
            "content_hash": hashlib.md5(content.encode()).hexdigest()[:16],
            "prompt_hash": hashlib.md5(prompt.encode()).hexdigest()[:16],
            "provider": self.provider.name,
            "model": self.provider.model,
            **kwargs,
        }

        # Sort keys for consistent hashing
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def extract_program_data_cached(
        self,
        content: str,
        prompt: Optional[str] = None,
        use_cache: bool = True,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Extract program data with caching.

        Args:
            content: Web page content to analyze
            prompt: Custom extraction prompt
            use_cache: Whether to use cache for this request
            ttl: Cache TTL in seconds (uses default if None)

        Returns:
            Extracted program data with caching metadata
        """
        if prompt is None:
            from ..core.constants import LLM_PROMPTS

            prompt = LLM_PROMPTS["program_extraction"]

        cache_key = self._make_cache_key(content, prompt)
        cache_ttl = ttl or self.default_ttl

        # Try cache first if enabled
        if self.cache_enabled and use_cache:
            cached_result = await self.cache.get(
                cache_key, self.namespaces["extractions"]
            )
            if cached_result is not None:
                logger.debug("Using cached LLM extraction result")
                cached_result["_cache_hit"] = True
                return cached_result

        # Cache miss - perform extraction
        start_time = time.time()
        result = await self.extract_program_data(content, prompt)
        extraction_time = time.time() - start_time

        # Add caching metadata
        result["_cache_hit"] = False
        result["_extraction_time"] = extraction_time
        result["_cached_at"] = time.time()

        # Cache the result if caching is enabled
        if self.cache_enabled and use_cache:
            try:
                await self.cache.set(
                    cache_key, result, cache_ttl, self.namespaces["extractions"]
                )
                logger.debug(f"Cached LLM extraction result (TTL: {cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Failed to cache extraction result: {e}")

        return result

    async def generate_completion_cached(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
        ttl: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate completion with caching.

        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            use_cache: Whether to use cache for this request
            ttl: Cache TTL in seconds
            **kwargs: Additional parameters

        Returns:
            Generated text response
        """
        cache_key = self._make_cache_key(
            "", prompt, temperature=temperature, max_tokens=max_tokens, **kwargs
        )
        cache_ttl = ttl or self.default_ttl

        # Try cache first if enabled
        if self.cache_enabled and use_cache:
            cached_result = await self.cache.get(
                cache_key, self.namespaces["completions"]
            )
            if cached_result is not None:
                logger.debug("Using cached LLM completion")
                return cached_result

        # Cache miss - generate completion
        result = await self.generate_completion(
            prompt, temperature, max_tokens, **kwargs
        )

        # Cache the result if caching is enabled
        if self.cache_enabled and use_cache:
            try:
                await self.cache.set(
                    cache_key, result, cache_ttl, self.namespaces["completions"]
                )
                logger.debug(f"Cached LLM completion (TTL: {cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Failed to cache completion: {e}")

        return result

    async def validate_data_quality_cached(
        self,
        data: Dict[str, Any],
        criteria: List[str],
        use_cache: bool = True,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Validate data quality with caching.

        Args:
            data: Data to validate
            criteria: Validation criteria
            use_cache: Whether to use cache
            ttl: Cache TTL in seconds

        Returns:
            Validation results
        """
        # Create cache key from data and criteria
        data_str = json.dumps(data, sort_keys=True)
        criteria_str = json.dumps(sorted(criteria), sort_keys=True)
        cache_key = self._make_cache_key(data_str, criteria_str)
        cache_ttl = ttl or self.default_ttl

        # Try cache first
        if self.cache_enabled and use_cache:
            cached_result = await self.cache.get(
                cache_key, self.namespaces["validations"]
            )
            if cached_result is not None:
                logger.debug("Using cached data validation result")
                return cached_result

        # Cache miss - perform validation
        result = await self.validate_data_quality(data, criteria)

        # Cache the result
        if self.cache_enabled and use_cache:
            try:
                await self.cache.set(
                    cache_key, result, cache_ttl, self.namespaces["validations"]
                )
                logger.debug(f"Cached data validation result (TTL: {cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Failed to cache validation result: {e}")

        return result

    async def generate_summary_cached(
        self,
        content: str,
        max_length: int = 300,
        use_cache: bool = True,
        ttl: Optional[int] = None,
    ) -> str:
        """
        Generate summary with caching.

        Args:
            content: Content to summarize
            max_length: Maximum summary length
            use_cache: Whether to use cache
            ttl: Cache TTL in seconds

        Returns:
            Generated summary
        """
        cache_key = self._make_cache_key(content, f"summary_{max_length}")
        cache_ttl = ttl or self.default_ttl

        # Try cache first
        if self.cache_enabled and use_cache:
            cached_result = await self.cache.get(
                cache_key, self.namespaces["summaries"]
            )
            if cached_result is not None:
                logger.debug("Using cached summary")
                return cached_result

        # Cache miss - generate summary
        result = await self.generate_summary(content, max_length)

        # Cache the result
        if self.cache_enabled and use_cache:
            try:
                await self.cache.set(
                    cache_key, result, cache_ttl, self.namespaces["summaries"]
                )
                logger.debug(f"Cached summary (TTL: {cache_ttl}s)")
            except Exception as e:
                logger.warning(f"Failed to cache summary: {e}")

        return result

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return await self.cache.get_stats()

    async def warmup_cache(self, common_prompts: List[str]) -> None:
        """
        Warm up the cache with common prompts.

        Args:
            common_prompts: List of prompts to pre-cache
        """
        logger.info(f"Warming up cache with {len(common_prompts)} prompts")

        for prompt in common_prompts:
            try:
                # Generate a simple completion to warm up
                await self.generate_completion_cached(
                    prompt,
                    temperature=0.1,
                    max_tokens=100,
                    use_cache=True,
                    ttl=self.default_ttl * 2,  # Longer TTL for warm-up entries
                )
                await asyncio.sleep(0.1)  # Small delay to avoid overwhelming the API
            except Exception as e:
                logger.warning(f"Failed to warm up cache for prompt: {e}")

        logger.info("Cache warm-up completed")

    async def invalidate_provider_cache(self) -> None:
        """Invalidate all cached entries for the current provider."""
        provider_namespace = f"llm:{self.provider.name}"
        await self.cache.clear(provider_namespace)
        logger.info(f"Invalidated cache for provider: {self.provider.name}")

    async def close(self) -> None:
        """Close the cached LLM service and its cache connections."""
        await self.cache.close()
        logger.info("Cached LLM service closed")
