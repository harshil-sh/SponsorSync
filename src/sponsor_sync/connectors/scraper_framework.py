"""Scraper connector framework primitives and request safety helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from sponsor_sync.connectors.base import JobQuery, RateLimiter, retry_operation
from sponsor_sync.models import JobPosting

T = TypeVar("T")


@dataclass(frozen=True)
class ScraperComplianceChecklist:
    """Robots/TOS compliance metadata that every scraper source must declare."""

    source_name: str
    robots_txt_url: str
    terms_of_service_url: str
    scraping_allowed: bool
    notes: str = ""


class BaseScraperConnector(ABC):
    """Contract all scrape-based connectors must implement."""

    source_name: str

    @property
    @abstractmethod
    def compliance_checklist(self) -> ScraperComplianceChecklist:
        """Return the source-specific robots/TOS compliance checklist."""

    @abstractmethod
    def fetch_jobs(self, query: JobQuery) -> list[JobPosting]:
        """Fetch jobs from the scraping source and return canonical postings."""


class ScraperRequestController:
    """Apply request throttling and retry backoff for scraper HTTP operations."""

    def __init__(
        self,
        *,
        min_interval_seconds: float = 1.0,
        attempts: int = 3,
        base_backoff_seconds: float = 0.5,
        retryable_exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts must be >= 1")
        if base_backoff_seconds < 0:
            raise ValueError("base_backoff_seconds must be >= 0")

        self._rate_limiter = RateLimiter(min_interval_seconds)
        self._attempts = attempts
        self._base_backoff_seconds = base_backoff_seconds
        self._retryable_exceptions = retryable_exceptions

    def execute(self, operation: Callable[[], T]) -> T:
        """Throttle request start time and retry transient failures with backoff."""
        self._rate_limiter.wait()
        return retry_operation(
            operation,
            attempts=self._attempts,
            retryable_exceptions=self._retryable_exceptions,
            backoff_seconds=self._base_backoff_seconds,
        )


def build_scraper_compliance_checklist(
    *,
    source_name: str,
    robots_txt_url: str,
    terms_of_service_url: str,
    scraping_allowed: bool,
    notes: str = "",
) -> ScraperComplianceChecklist:
    """Validate and construct a source compliance checklist."""
    _require_http_url("robots_txt_url", robots_txt_url)
    _require_http_url("terms_of_service_url", terms_of_service_url)
    if not source_name.strip():
        raise ValueError("source_name is required")

    return ScraperComplianceChecklist(
        source_name=source_name.strip(),
        robots_txt_url=robots_txt_url,
        terms_of_service_url=terms_of_service_url,
        scraping_allowed=scraping_allowed,
        notes=notes.strip(),
    )


def _require_http_url(field_name: str, value: str) -> None:
    if not value.startswith(("http://", "https://")):
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")
