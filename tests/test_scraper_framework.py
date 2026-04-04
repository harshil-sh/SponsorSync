from __future__ import annotations

from sponsor_sync.connectors.base import JobQuery
from sponsor_sync.connectors.scraper_framework import (
    BaseScraperConnector,
    ScraperRequestController,
    build_scraper_compliance_checklist,
)


class _FakeScraper(BaseScraperConnector):
    source_name = "fake-board"

    @property
    def compliance_checklist(self):
        return build_scraper_compliance_checklist(
            source_name=self.source_name,
            robots_txt_url="https://example.com/robots.txt",
            terms_of_service_url="https://example.com/terms",
            scraping_allowed=True,
            notes="Public board allows crawling with throttling.",
        )

    def fetch_jobs(self, query: JobQuery):
        del query
        return []


def test_scraper_connector_declares_compliance_checklist() -> None:
    scraper = _FakeScraper()

    checklist = scraper.compliance_checklist
    assert checklist.source_name == "fake-board"
    assert checklist.scraping_allowed is True
    assert checklist.robots_txt_url.endswith("robots.txt")


def test_scraper_request_controller_retries_operation() -> None:
    attempts = 0

    def flaky_fetch() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary failure")
        return "ok"

    controller = ScraperRequestController(
        min_interval_seconds=0,
        attempts=3,
        base_backoff_seconds=0,
        retryable_exceptions=(TimeoutError,),
    )

    assert controller.execute(flaky_fetch) == "ok"
    assert attempts == 3


def test_compliance_checklist_requires_absolute_urls() -> None:
    try:
        build_scraper_compliance_checklist(
            source_name="source",
            robots_txt_url="/robots.txt",
            terms_of_service_url="https://example.com/terms",
            scraping_allowed=False,
        )
    except ValueError as exc:
        assert "robots_txt_url" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-absolute robots URL")
