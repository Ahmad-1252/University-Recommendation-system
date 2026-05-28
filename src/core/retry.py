"""Retry policy framework with exponential backoff and jitter."""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional

from .exceptions import BaseError, ErrorContext

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass
class RetryConfig:
    """Configuration for retry policies."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_errors: Optional[List[str]] = None  # Error codes that are retryable


class RetryPolicy(ABC):
    """Abstract base class for retry policies."""

    def __init__(self, config: RetryConfig):
        self.config = config

    @abstractmethod
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        pass

    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if error should be retried."""
        if attempt >= self.config.max_attempts:
            return False

        # Check if error is retryable based on error code
        if isinstance(error, BaseError):
            if self.config.retryable_errors:
                return error.error_code in self.config.retryable_errors
            # Default retry logic based on error properties
            return error.context.recoverable

        # For non-BaseError exceptions, retry by default
        return True

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt."""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.initial_delay
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * (attempt + 1)
        else:  # EXPONENTIAL
            delay = self.config.initial_delay * (self.config.backoff_factor**attempt)

        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


class ExponentialBackoffRetry(RetryPolicy):
    """Retry policy with exponential backoff."""

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry."""
        last_error = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e

                if not self._should_retry(e, attempt):
                    logger.debug(f"Not retrying error (attempt {attempt + 1}): {e}")
                    break

                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise last_error


class CircuitBreakerRetry(ExponentialBackoffRetry):
    """Retry policy integrated with circuit breaker."""

    def __init__(self, config: RetryConfig, circuit_breaker: "CircuitBreaker"):
        super().__init__(config)
        self.circuit_breaker = circuit_breaker

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        # Check if circuit is open
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is open for {self.circuit_breaker.name}",
                context=ErrorContext(
                    operation="circuit_breaker_check",
                    component=self.circuit_breaker.name,
                ),
            )

        try:
            result = await super().execute(func, *args, **kwargs)
            await self.circuit_breaker.record_success()
            return result
        except Exception:
            await self.circuit_breaker.record_failure()
            raise


# Convenience functions for common retry patterns
async def retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_errors: Optional[List[str]] = None,
    *args,
    **kwargs,
) -> Any:
    """Convenience function for exponential backoff retry."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        jitter=jitter,
        retryable_errors=retryable_errors,
    )

    policy = ExponentialBackoffRetry(config)
    return await policy.execute(func, *args, **kwargs)


# Import here to avoid circular imports
from .exceptions import CircuitBreakerError


class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when circuit breaker is open."""

    pass
