"""LLM provider factory for creating provider instances."""

from typing import Optional
from .base_provider import LLMProvider
from .groq_provider import GroqProvider
from .deepseek_provider import DeepSeekProvider
from core.config import get_settings


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    @staticmethod
    def create_provider(provider_name: Optional[str] = None) -> LLMProvider:
        """
        Create an LLM provider instance based on configuration.

        Args:
            provider_name: Override provider name, uses config if None

        Returns:
            LLMProvider instance

        Raises:
            ValueError: If provider is not supported or not configured
        """
        settings = get_settings()

        if provider_name is None:
            provider_name = settings.llm.provider

        provider_name = provider_name.lower()

        if provider_name == "groq":
            if not settings.llm.groq.api_key:
                raise ValueError("Groq API key not configured")
            return GroqProvider(
                api_key=settings.llm.groq.api_key,
                model=settings.llm.groq.model,
                timeout=settings.llm.groq.timeout
            )

        elif provider_name == "deepseek":
            if not settings.llm.deepseek.api_key:
                raise ValueError("DeepSeek API key not configured")
            return DeepSeekProvider(
                api_key=settings.llm.deepseek.api_key,
                model=settings.llm.deepseek.model,
                timeout=settings.llm.deepseek.timeout
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")

    @staticmethod
    async def create_provider_with_fallback(primary_provider: Optional[str] = None) -> LLMProvider:
        """
        Create provider with automatic fallback to alternative provider.

        Args:
            primary_provider: Primary provider to try first

        Returns:
            LLMProvider instance (primary or fallback)

        Raises:
            ValueError: If no providers are configured
        """
        settings = get_settings()

        providers_to_try = []
        if primary_provider:
            providers_to_try.append(primary_provider.lower())
        else:
            providers_to_try.append(settings.llm.provider.lower())

        # Add fallback providers
        available_providers = ["groq", "deepseek"]
        for provider in available_providers:
            if provider not in providers_to_try:
                providers_to_try.append(provider)

        for provider_name in providers_to_try:
            try:
                provider = LLMProviderFactory.create_provider(provider_name)
                # Validate connection
                if await provider.validate_connection():
                    return provider
            except Exception:
                continue  # Try next provider

        raise ValueError("No LLM providers are available or configured")

    @staticmethod
    def get_available_providers() -> list[str]:
        """
        Get list of available (configured) providers.

        Returns:
            List of provider names that are configured
        """
        settings = get_settings()
        available = []

        if settings.llm.groq.api_key:
            available.append("groq")
        if settings.llm.deepseek.api_key:
            available.append("deepseek")

        return available