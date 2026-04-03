"""Base connector primitives and shared API connector helpers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from sponsor_sync.models import JobPosting

T = TypeVar("T")


@dataclass(frozen=True)
class JobQuery:
    """Search query parameters passed to source connectors."""

    keywords: str
    location: str
    page_size: int = 25


class BaseConnector(ABC):
    """Contract all source connectors must implement."""

    source_name: str

    @abstractmethod
    def fetch_jobs(self, query: JobQuery) -> list[JobPosting]:
        """Fetch jobs from the connector source and return canonical postings."""


class RateLimiter:
    """Simple monotonic-clock rate limiter for API requests."""

    def __init__(self, min_interval_seconds: float) -> None:
        if min_interval_seconds < 0:
            raise ValueError("min_interval_seconds must be >= 0")

        self._min_interval_seconds = min_interval_seconds
        self._last_call_started: float | None = None

    def wait(self) -> None:
        """Sleep as needed so calls are separated by at least min_interval_seconds."""
        if self._last_call_started is None:
            self._last_call_started = time.monotonic()
            return

        elapsed = time.monotonic() - self._last_call_started
        remaining = self._min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

        self._last_call_started = time.monotonic()


def retry_operation(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    backoff_seconds: float = 0.5,
) -> T:
    """Run operation with retry/backoff semantics for transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retryable_exceptions:
            if attempt == attempts:
                raise
            time.sleep(backoff_seconds * attempt)

    raise RuntimeError("retry_operation exhausted without returning")
