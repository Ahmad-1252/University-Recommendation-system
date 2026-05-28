import json
import logging
import time

from groq import APIError, AuthenticationError, Groq, RateLimitError

from .base_provider import LLMError, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    """Groq LLM provider implementation using llama3 models."""

    def __init__(
        self, api_key: str, model: str = "llama-3.3-70b-versatile", timeout: int = 120
    ):
        super().__init__("groq", model, api_key, timeout)
        self.client = Groq(api_key=api_key, timeout=timeout)

    async def extract_program_data(self, content: str, prompt: str) -> LLMResponse:
        """
        Extract program data using Groq LLM.

        Args:
            content: Web page content
            prompt: Extraction prompt

        Returns:
            LLMResponse with extracted data

        Raises:
            LLMError: If extraction fails
        """
        start_time = time.time()

        try:
            # Content truncation guard — keep content under ~25K tokens
            max_content_chars = 80000
            if len(content) > max_content_chars:
                logger.warning(
                    f"Content truncated from {len(content)} to {max_content_chars} chars"
                )
                content = content[:max_content_chars] + "... [TRUNCATED]"

            # Create the full prompt
            full_prompt = f"{prompt}\n\nContent to analyze:\n{content}"

            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from university program web pages. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": full_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=min(self.max_tokens, 4000),  # Limit response size
                timeout=self.timeout,
            )

            # Extract response content
            response_content = response.choices[0].message.content.strip()

            # Calculate confidence score based on response characteristics
            confidence_score = self._calculate_confidence_score(response_content)

            # Calculate processing time
            processing_time = time.time() - start_time

            return LLMResponse(
                content=response_content,
                confidence_score=confidence_score,
                provider_name=self.name,
                model_name=self.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                processing_time=processing_time,
            )

        except AuthenticationError as e:
            raise LLMError(
                provider_name=self.name,
                error_type="authentication",
                message=f"Invalid API key: {str(e)}",
                retryable=False,
            )
        except RateLimitError as e:
            raise LLMError(
                provider_name=self.name,
                error_type="rate_limit",
                message=f"Rate limit exceeded: {str(e)}",
                retryable=True,
            )
        except APIError as e:
            raise LLMError(
                provider_name=self.name,
                error_type="api_error",
                message=f"API error: {str(e)}",
                retryable=True,
            )
        except Exception as e:
            raise LLMError(
                provider_name=self.name,
                error_type="unknown",
                message=f"Unexpected error: {str(e)}",
                retryable=True,
            )

    async def validate_connection(self) -> bool:
        """Validate Groq API connection."""
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
            )
            return True
        except Exception:
            return False

    async def get_token_count(self, text: str) -> int:
        """Estimate token count for Groq (improved approximation)."""
        # Conservative approximation: ~0.3 tokens per character is safer for university content.
        return int(len(text) * 0.3)

    @property
    def max_tokens(self) -> int:
        """Maximum tokens for Groq llama3-70b model."""
        return 8192

    @property
    def cost_per_token(self) -> float:
        """Cost per token for Groq (as of 2025)."""
        # Groq pricing: $0.70 per million tokens for llama3-70b
        return 0.70 / 1_000_000

    def _calculate_confidence_score(self, response_content: str) -> float:
        """
        Calculate confidence score based on response characteristics.

        Args:
            response_content: Raw LLM response

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.5  # Base score

        try:
            # Try to parse as JSON
            json.loads(response_content)
            score += 0.3  # Valid JSON increases confidence
        except json.JSONDecodeError:
            score -= 0.2  # Invalid JSON decreases confidence

        # Check for structured content indicators
        if any(
            keyword in response_content.lower()
            for keyword in [
                "university",
                "program",
                "degree",
                "requirements",
                "tuition",
            ]
        ):
            score += 0.1

        # Length check (too short responses are suspicious)
        if len(response_content) < 50:
            score -= 0.2
        elif len(response_content) > 200:
            score += 0.1

        return max(0.0, min(1.0, score))
