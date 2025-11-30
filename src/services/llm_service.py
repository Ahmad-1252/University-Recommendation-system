"""LLM service with provider abstraction and enhanced features."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
import hashlib
import json

from ..core.config import get_settings
from ..core.exceptions import (
    GroqAPIError,
    RateLimitError,
    DeepSeekAPIError,
    ErrorContext,
    NetworkError,
    TimeoutError
)
from ..core.constants import LLM_PROMPTS
from ..core.retry import retry_with_backoff, RetryConfig
from ..core.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
from .llm import LLMProviderFactory, LLMProvider, LLMResponse, LLMError

logger = logging.getLogger(__name__)


class LLMService:
    """Enhanced LLM service with provider abstraction and caching."""

    def __init__(self, provider: Optional[LLMProvider] = None, use_cache: bool = True):
        self.settings = get_settings()

        # Initialize provider (deferred to avoid event loop issues)
        self._provider = provider
        self._provider_initialized = provider is not None

        # Legacy settings for backward compatibility (will be set after provider init)
        self.model = "unknown"
        self.timeout = 30
        self.max_retries = self.settings.llm.max_retries
        self.temperature = self.settings.llm.temperature
        self.rate_limit_delay = 1.0  # Default rate limit delay

        # Initialize cache if requested
        self._cache = None
        self._cache_enabled = False
        if use_cache:
            try:
                from .cache import CacheFactory
                self._cache = CacheFactory.create_cache()
                self._cache_enabled = True
                logger.info("LLM service cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize cache: {e}")

        # Initialize circuit breaker for API calls
        self._circuit_breaker = None
        if self.settings.error_handling.enable_circuit_breakers:
            try:
                circuit_config = CircuitBreakerConfig(
                    failure_threshold=self.settings.error_handling.circuit_failure_threshold,
                    recovery_timeout=self.settings.error_handling.circuit_recovery_timeout,
                    success_threshold=self.settings.error_handling.circuit_success_threshold,
                    timeout=self.settings.error_handling.circuit_timeout,
                    name="llm_api"
                )
                self._circuit_breaker = get_circuit_breaker("llm_api", circuit_config)
                logger.info("LLM service circuit breaker initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize circuit breaker: {e}")

        # Cache namespaces
        self._namespaces = {
            "completions": "llm:completions",
            "extractions": "llm:extractions",
            "validations": "llm:validations",
            "summaries": "llm:summaries"
        }

    @property
    def provider(self) -> LLMProvider:
        """Get the LLM provider, initializing it if necessary."""
        if not self._provider_initialized:
            # For now, create a simple provider directly to avoid async issues
            # In production, this should be initialized asynchronously
            try:
                self._provider = LLMProviderFactory.create_provider()
                self._provider_initialized = True

                # Update legacy settings
                self.model = self._provider.model
                self.timeout = self._provider.timeout

                logger.info(f"Initialized LLM service with provider: {self._provider.name}")
            except ValueError as e:
                logger.error(f"Failed to initialize LLM provider: {e}")
                raise
        return self._provider

    @provider.setter
    def provider(self, value: LLMProvider) -> None:
        """Set the LLM provider."""
        self._provider = value
        self._provider_initialized = True
        self.model = value.model
        self.timeout = value.timeout

    def enable_cache(self) -> None:
        """Enable response caching."""
        if self._cache:
            self._cache_enabled = True
            logger.info("LLM response caching enabled")
        else:
            logger.warning("Cache backend not available")

    def disable_cache(self) -> None:
        """Disable response caching."""
        self._cache_enabled = False
        logger.info("LLM response caching disabled")

    async def clear_cache(self) -> None:
        """Clear the response cache."""
        if self._cache:
            await self._cache.clear()
            logger.info("LLM response cache cleared")
        else:
            logger.warning("Cache backend not available")

    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """Generate cache key from prompt and parameters."""
        key_data = {
            "prompt": prompt,
            "provider": self.provider.name,
            "model": self.provider.model,
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
        Generate a completion using the configured LLM provider.

        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated text response

        Raises:
            GroqAPIError: Legacy exception for backward compatibility
            DeepSeekAPIError: For DeepSeek provider errors
            RateLimitError: When rate limits are exceeded
            NetworkError: For network-related issues
        """
        # Check cache first
        if self._cache_enabled and self._cache:
            cache_key = self._get_cache_key(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
            try:
                cached_response = await self._cache.get(cache_key, self._namespaces["completions"])
                if cached_response is not None:
                    logger.debug("Using cached LLM response")
                    return cached_response
            except Exception as e:
                logger.debug(f"Cache retrieval failed: {e}")

        # Cache miss - use retry framework with circuit breaker
        async def _api_call() -> str:
            """Make the actual API call with error handling."""
            try:
                logger.debug(f"Making LLM API call with provider {self.provider.name}")

                # Use provider's extract_program_data method (adapted for general completion)
                full_prompt = f"Please respond to the following request:\n\n{prompt}"

                response: LLMResponse = await self.provider.extract_program_data(
                    content="",  # Empty content for general completion
                    prompt=full_prompt
                )

                generated_text = response.content

                # Rate limiting delay
                await asyncio.sleep(self.rate_limit_delay)

                return generated_text

            except LLMError as e:
                # Convert LLMError to appropriate BaseError
                error_context = ErrorContext(
                    operation="generate_completion",
                    component=f"llm_provider_{self.provider.name}",
                    metadata={
                        "provider": self.provider.name,
                        "model": self.provider.model,
                        "prompt_length": len(prompt)
                    }
                )

                if e.error_type == "rate_limit":
                    raise RateLimitError(
                        f"Rate limit exceeded: {e.message}",
                        context=error_context
                    ) from e
                elif e.error_type == "timeout":
                    raise TimeoutError(
                        f"Request timeout: {e.message}",
                        context=error_context
                    ) from e
                elif e.error_type == "network":
                    raise NetworkError(
                        f"Network error: {e.message}",
                        context=error_context
                    ) from e
                else:
                    # Provider-specific errors
                    if "groq" in self.provider.name.lower():
                        raise GroqAPIError(
                            f"Groq API error: {e.message}",
                            context=error_context
                        ) from e
                    elif "deepseek" in self.provider.name.lower():
                        raise DeepSeekAPIError(
                            f"DeepSeek API error: {e.message}",
                            context=error_context
                        ) from e
                    else:
                        raise GroqAPIError(
                            f"LLM API error: {e.message}",
                            context=error_context
                        ) from e

        try:
            # Configure retry policy
            retry_config = RetryConfig(
                max_attempts=self.settings.error_handling.default_max_retries,
                initial_delay=self.settings.error_handling.default_retry_delay,
                max_delay=self.settings.error_handling.default_max_retry_delay,
                backoff_factor=self.settings.error_handling.default_backoff_factor,
                retryable_errors=["API_002", "API_003", "API_004", "NET_001", "NET_002"]  # API and network errors
            )

            # Execute with retry and circuit breaker
            if self._circuit_breaker:
                # Use circuit breaker retry
                from ..core.retry import CircuitBreakerRetry
                retry_policy = CircuitBreakerRetry(retry_config, self._circuit_breaker)
                generated_text = await retry_policy.execute(_api_call)
            else:
                # Use simple exponential backoff retry
                generated_text = await retry_with_backoff(
                    _api_call,
                    max_attempts=retry_config.max_attempts,
                    initial_delay=retry_config.initial_delay,
                    backoff_factor=retry_config.backoff_factor,
                    max_delay=retry_config.max_delay,
                    retryable_errors=retry_config.retryable_errors
                )

            # Cache the response if caching is enabled
            if self._cache_enabled and self._cache:
                try:
                    cache_key = self._get_cache_key(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
                    await self._cache.set(cache_key, generated_text, None, self._namespaces["completions"])
                    logger.debug("Cached LLM response")
                except Exception as e:
                    logger.debug(f"Cache storage failed: {e}")

            return generated_text

        except RateLimitError:
            # Re-raise rate limit errors as-is
            raise
        except (GroqAPIError, DeepSeekAPIError):
            # Re-raise provider-specific errors as-is for backward compatibility
            raise
        except Exception as e:
            # Wrap any other errors
            logger.error(f"Unexpected error in generate_completion: {e}")
            raise GroqAPIError(f"LLM completion failed: {str(e)}") from e

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

    async def extract_program_data(self,
                                 content: str,
                                 prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract program data using the LLM provider.

        Args:
            content: Web page content to analyze
            prompt: Custom extraction prompt

        Returns:
            Extracted program data as dict
        """
        if prompt is None:
            prompt = LLM_PROMPTS["program_extraction"]

        try:
            response: LLMResponse = await self.provider.extract_program_data(content, prompt)

            # Try to parse the response as JSON
            try:
                data = json.loads(response.content)
                # Add metadata
                data["_metadata"] = {
                    "confidence_score": response.confidence_score,
                    "provider": response.provider_name,
                    "model": response.model_name,
                    "tokens_used": response.tokens_used,
                    "processing_time": response.processing_time
                }
                return data
            except json.JSONDecodeError:
                logger.warning("LLM response is not valid JSON, attempting to extract JSON from text")
                # Try to extract JSON from the response
                json_start = response.content.find('{')
                json_end = response.content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response.content[json_start:json_end]
                    data = json.loads(json_str)
                    # Add metadata
                    data["_metadata"] = {
                        "confidence_score": response.confidence_score,
                        "provider": response.provider_name,
                        "model": response.model_name,
                        "tokens_used": response.tokens_used,
                        "processing_time": response.processing_time
                    }
                    return data
                else:
                    raise ValueError("No JSON found in LLM response")

        except LLMError as e:
            logger.error(f"Program data extraction failed: {e}")
            raise GroqAPIError(f"Data extraction failed: {e.message}") from e

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

    def switch_provider(self, provider_name: str) -> None:
        """
        Switch to a different LLM provider.

        Args:
            provider_name: Name of the provider to switch to

        Raises:
            ValueError: If provider is not available
        """
        try:
            new_provider = LLMProviderFactory.create_provider(provider_name)
            self.provider = new_provider
            self.model = new_provider.model
            self.timeout = new_provider.timeout
            logger.info(f"Switched to LLM provider: {provider_name}")
        except ValueError as e:
            logger.error(f"Failed to switch provider: {e}")
            raise

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._cache:
            return await self._cache.get_stats()
        return {"cache_enabled": False, "error": "Cache backend not available"}

    async def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        if self._circuit_breaker:
            return self._circuit_breaker.get_stats()
        return {"circuit_breaker_enabled": False, "error": "Circuit breaker not available"}

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            "provider": self.provider.name,
            "model": self.provider.model,
            "timeout": self.provider.timeout,
            "max_retries": self.max_retries,
            "rate_limit_delay": self.rate_limit_delay,
            "cache_enabled": self._cache_enabled,
            "cache_backend_available": self._cache is not None,
            "circuit_breaker_enabled": self._circuit_breaker is not None,
            "available_providers": LLMProviderFactory.get_available_providers(),
            "error_handling_config": {
                "max_retries": self.settings.error_handling.default_max_retries,
                "retry_delay": self.settings.error_handling.default_retry_delay,
                "max_retry_delay": self.settings.error_handling.default_max_retry_delay,
                "backoff_factor": self.settings.error_handling.default_backoff_factor,
                "circuit_breakers_enabled": self.settings.error_handling.enable_circuit_breakers
            }
        }