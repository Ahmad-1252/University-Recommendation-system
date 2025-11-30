"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LLMResponse:
    """Standardized response from LLM providers."""
    content: str
    confidence_score: float
    provider_name: str
    model_name: str
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class LLMError(Exception):
    """Standardized error from LLM providers."""
    
    def __init__(
        self,
        provider_name: str,
        error_type: str,
        message: str,
        retryable: bool = True,
        timestamp: datetime = None
    ):
        super().__init__(message)
        self.provider_name = provider_name
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
        self.timestamp = timestamp or datetime.now()
    
    def __str__(self):
        return f"[{self.provider_name}] {self.error_type}: {self.message}"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, name: str, model: str, api_key: str, timeout: int = 30):
        self.name = name
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    async def extract_program_data(self, content: str, prompt: str) -> LLMResponse:
        """
        Extract program data from web content using LLM.

        Args:
            content: The web page content to analyze
            prompt: The extraction prompt to use

        Returns:
            LLMResponse with extracted data

        Raises:
            LLMError: If extraction fails
        """
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the provider connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        pass

    @abstractmethod
    async def get_token_count(self, text: str) -> int:
        """
        Estimate token count for given text.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        pass

    @property
    @abstractmethod
    def max_tokens(self) -> int:
        """Maximum tokens supported by this provider."""
        pass

    @property
    @abstractmethod
    def cost_per_token(self) -> float:
        """Cost per token in USD (for cost tracking)."""
        pass
    
    async def close(self) -> None:
        """Close any resources used by the provider. Override if needed."""
        pass  # Default implementation does nothing