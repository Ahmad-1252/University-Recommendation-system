"""DeepSeek LLM provider implementation."""

import json
import time
from typing import Dict, Any, Optional
import hashlib

import httpx

from .base_provider import LLMProvider, LLMResponse, LLMError


class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider implementation using their API."""

    def __init__(self, api_key: str, model: str = "deepseek-chat", timeout: int = 30):
        super().__init__("deepseek", model, api_key, timeout)
        self.base_url = "https://api.deepseek.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout
        )

    async def extract_program_data(self, content: str, prompt: str) -> LLMResponse:
        """
        Extract program data using DeepSeek LLM.

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
            # Create the full prompt
            full_prompt = f"{prompt}\n\nContent to analyze:\n{content}"

            # Prepare request payload
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert at extracting structured data from university program web pages. Always respond with valid JSON."},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": 0.1,  # Low temperature for consistent extraction
                "max_tokens": min(self.max_tokens, 4000),  # Limit response size
                "stream": False
            }

            # Make API call
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            data = response.json()

            # Extract response content
            response_content = data["choices"][0]["message"]["content"].strip()

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(response_content)

            # Calculate processing time
            processing_time = time.time() - start_time

            return LLMResponse(
                content=response_content,
                confidence_score=confidence_score,
                provider_name=self.name,
                model_name=self.model,
                tokens_used=data.get("usage", {}).get("total_tokens"),
                processing_time=processing_time
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMError(
                    provider_name=self.name,
                    error_type="authentication",
                    message=f"Invalid API key: {e.response.text}",
                    retryable=False
                )
            elif e.response.status_code == 429:
                raise LLMError(
                    provider_name=self.name,
                    error_type="rate_limit",
                    message=f"Rate limit exceeded: {e.response.text}",
                    retryable=True
                )
            else:
                raise LLMError(
                    provider_name=self.name,
                    error_type="api_error",
                    message=f"API error ({e.response.status_code}): {e.response.text}",
                    retryable=True
                )
        except httpx.TimeoutException:
            raise LLMError(
                provider_name=self.name,
                error_type="timeout",
                message="Request timed out",
                retryable=True
            )
        except Exception as e:
            raise LLMError(
                provider_name=self.name,
                error_type="unknown",
                message=f"Unexpected error: {str(e)}",
                retryable=True
            )

    async def validate_connection(self) -> bool:
        """Validate DeepSeek API connection."""
        try:
            # Simple test call
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return True
        except Exception:
            return False

    async def get_token_count(self, text: str) -> int:
        """Estimate token count for DeepSeek (rough approximation)."""
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    @property
    def max_tokens(self) -> int:
        """Maximum tokens for DeepSeek models."""
        return 4096  # DeepSeek has lower context limits

    @property
    def cost_per_token(self) -> float:
        """Cost per token for DeepSeek (as of 2025)."""
        # DeepSeek pricing: $0.14 per million tokens for deepseek-chat
        return 0.14 / 1_000_000

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
        if any(keyword in response_content.lower() for keyword in [
            "university", "program", "degree", "requirements", "tuition"
        ]):
            score += 0.1

        # Length check (too short responses are suspicious)
        if len(response_content) < 50:
            score -= 0.2
        elif len(response_content) > 200:
            score += 0.1

        return max(0.0, min(1.0, score))