"""UK-only scraper connector for Indeed, Totaljobs, and LinkedIn Jobs."""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timezone

from sponsor_sync.connectors.base import JobQuery
from sponsor_sync.connectors.scraper_framework import (
    BaseScraperConnector,
    ScraperComplianceChecklist,
    ScraperRequestController,
    build_scraper_compliance_checklist,
)
from sponsor_sync.models import JobPosting
from sponsor_sync.utilities import (
    normalize_contract_type,
    normalize_title,
    parse_salary_to_annual_gbp,
)

_SOURCE_URLS = {
    "indeed_uk": "https://uk.indeed.com/jobs",
    "totaljobs_uk": "https://www.totaljobs.com/jobs",
    "linkedin_jobs_uk": "https://www.linkedin.com/jobs/search",
}

_SOURCE_HOSTS = {
    "indeed_uk": "https://uk.indeed.com",
    "totaljobs_uk": "https://www.totaljobs.com",
    "linkedin_jobs_uk": "https://www.linkedin.com",
}

_UK_LOCATION_MARKERS = {
    "uk",
    "united kingdom",
    "england",
    "scotland",
    "wales",
    "northern ireland",
    "london",
    "manchester",
    "birmingham",
    "leeds",
    "bristol",
    "glasgow",
    "edinburgh",
    "liverpool",
    "newcastle",
    "cardiff",
    "belfast",
}


class UkJobBoardsScraperConnector(BaseScraperConnector):
    """Scrape and normalize job listings from selected UK job boards."""

    source_name = "uk_job_boards"

    def __init__(
        self,
        *,
        page_fetcher: Callable[[str], str],
        request_controller: ScraperRequestController | None = None,
        salary_threshold_gbp: float = 45_000,
    ) -> None:
        self._page_fetcher = page_fetcher
        self._request_controller = request_controller or ScraperRequestController()
        self._salary_threshold_gbp = salary_threshold_gbp

    @property
    def compliance_checklist(self) -> ScraperComplianceChecklist:
        return build_scraper_compliance_checklist(
            source_name=self.source_name,
            robots_txt_url="https://uk.indeed.com/robots.txt",
            terms_of_service_url="https://www.indeed.com/legal",
            scraping_allowed=False,
            notes=(
                "Connector is parser-ready for Indeed UK, Totaljobs UK, and "
                "LinkedIn Jobs UK; run only where source TOS/robots allow and "
                "with explicit compliance review."
            ),
        )

    def fetch_jobs(self, query: JobQuery) -> list[JobPosting]:
        """Fetch list/detail pages from UK-only sources."""
        if not _is_uk_location(query.location):
            raise ValueError("UkJobBoardsScraperConnector supports UK locations only")

        jobs: list[JobPosting] = []
        for source, base_url in _SOURCE_URLS.items():
            list_url = self._build_list_url(base_url, query)
            list_html = self._request_controller.execute(
                lambda url=list_url: self._page_fetcher(url)
            )
            for listing in self.parse_list_page(source, list_html):
                detail_html = self._request_controller.execute(
                    lambda url=listing["url"]: self._page_fetcher(url)
                )
                detail = self.parse_detail_page(source, detail_html)
                jobs.append(self._to_job_posting(source, listing, detail))

        return jobs

    def _build_list_url(self, base_url: str, query: JobQuery) -> str:
        encoded_keywords = urllib.parse.quote_plus(query.keywords)
        encoded_location = urllib.parse.quote_plus(query.location)
        return f"{base_url}?keywords={encoded_keywords}&location={encoded_location}"

    def parse_list_page(self, source: str, html: str) -> list[dict[str, str]]:
        """Extract summary metadata from a source list page."""
        if source == "indeed_uk":
            return _parse_indeed_list(html)
        if source == "totaljobs_uk":
            return _parse_totaljobs_list(html)
        if source == "linkedin_jobs_uk":
            return _parse_linkedin_list(html)
        raise ValueError(f"Unsupported source: {source}")

    def parse_detail_page(self, source: str, html: str) -> dict[str, str]:
        """Extract rich metadata from a source detail page."""
        if source == "indeed_uk":
            return _parse_indeed_detail(html)
        if source == "totaljobs_uk":
            return _parse_totaljobs_detail(html)
        if source == "linkedin_jobs_uk":
            return _parse_linkedin_detail(html)
        raise ValueError(f"Unsupported source: {source}")

    def _to_job_posting(
        self, source: str, listing: dict[str, str], detail: dict[str, str]
    ) -> JobPosting:
        salary_text = detail.get("salary") or listing.get("salary") or ""
        parsed_salary = parse_salary_to_annual_gbp(salary_text)

        employment_raw = detail.get("employment_type") or listing.get(
            "employment_type", ""
        )
        employment_type = normalize_contract_type(employment_raw)

        salary_min = parsed_salary.minimum_gbp
        salary_max = parsed_salary.maximum_gbp
        passes_salary_threshold = bool(
            (salary_min is not None and salary_min > self._salary_threshold_gbp)
            or (salary_max is not None and salary_max > self._salary_threshold_gbp)
        )

        return JobPosting(
            job_id=f"{source}:{listing['source_job_id']}",
            source=source,
            source_job_id=listing["source_job_id"],
            title=listing["title"],
            company=listing["company"],
            location=listing["location"],
            employment_type=employment_type,
            salary_min_gbp=salary_min,
            salary_max_gbp=salary_max,
            salary_currency=(
                "GBP" if salary_min is not None or salary_max is not None else None
            ),
            salary_period=(
                "annual" if salary_min is not None or salary_max is not None else None
            ),
            description=detail.get("description", "No description provided"),
            posted_at=None,
            url=listing["url"],
            scraped_at=datetime.now(timezone.utc),
            normalized_title=normalize_title(listing["title"]),
            is_permanent=employment_type == "permanent",
            passes_salary_threshold=passes_salary_threshold,
        )


def _is_uk_location(location: str) -> bool:
    lowered = location.strip().lower()
    return any(marker in lowered for marker in _UK_LOCATION_MARKERS)


def _parse_indeed_list(html: str) -> list[dict[str, str]]:
    cards = re.findall(
        r'<div class="job_seen_beacon"[^>]*>.*?</div>\s*</div>', html, re.S
    )
    results: list[dict[str, str]] = []
    for card in cards:
        source_job_id = _extract_first(card, r'data-jk="([^"]+)"')
        title = _strip_html(_extract_first(card, r'title="([^"]+)"'))
        company = _strip_html(
            _extract_first(card, r'data-testid="company-name">(.*?)<')
        )
        location = _strip_html(
            _extract_first(card, r'data-testid="text-location">(.*?)<')
        )
        salary = _strip_html(
            _extract_first(card, r'data-testid="attribute_snippet_testid">(.*?)<')
        )
        href = _extract_first(card, r'href="([^"]+)"')

        if source_job_id and title and href:
            results.append(
                {
                    "source_job_id": source_job_id,
                    "title": title,
                    "company": company or "Unknown employer",
                    "location": location or "United Kingdom",
                    "salary": salary,
                    "employment_type": "",
                    "url": _absolute_url("indeed_uk", href),
                }
            )
    return results


def _parse_totaljobs_list(html: str) -> list[dict[str, str]]:
    cards = re.findall(r'<article class="job"[^>]*>.*?</article>', html, re.S)
    results: list[dict[str, str]] = []
    for card in cards:
        source_job_id = _extract_first(card, r'data-job-id="([^"]+)"')
        title = _strip_html(_extract_first(card, r'class="job-title"[^>]*>(.*?)<'))
        company = _strip_html(_extract_first(card, r'class="company"[^>]*>(.*?)<'))
        location = _strip_html(_extract_first(card, r'class="location"[^>]*>(.*?)<'))
        salary = _strip_html(_extract_first(card, r'class="salary"[^>]*>(.*?)<'))
        contract = _strip_html(_extract_first(card, r'class="contract"[^>]*>(.*?)<'))
        href = _extract_first(card, r'href="([^"]+)"')

        if source_job_id and title and href:
            results.append(
                {
                    "source_job_id": source_job_id,
                    "title": title,
                    "company": company or "Unknown employer",
                    "location": location or "United Kingdom",
                    "salary": salary,
                    "employment_type": contract,
                    "url": _absolute_url("totaljobs_uk", href),
                }
            )
    return results


def _parse_linkedin_list(html: str) -> list[dict[str, str]]:
    cards = re.findall(
        r'<li[^>]*data-occludable-job-id="[^"]+"[^>]*>.*?</li>', html, re.S
    )
    results: list[dict[str, str]] = []
    for card in cards:
        source_job_id = _extract_first(card, r'data-occludable-job-id="([^"]+)"')
        title = _strip_html(
            _extract_first(card, r'class="base-search-card__title"[^>]*>(.*?)<')
        )
        company = _strip_html(
            _extract_first(card, r'class="base-search-card__subtitle"[^>]*>(.*?)<')
        )
        location = _strip_html(
            _extract_first(card, r'class="job-search-card__location"[^>]*>(.*?)<')
        )
        href = _extract_first(card, r'class="base-card__full-link"[^>]*href="([^"]+)"')

        if source_job_id and title and href:
            results.append(
                {
                    "source_job_id": source_job_id,
                    "title": title,
                    "company": company or "Unknown employer",
                    "location": location or "United Kingdom",
                    "salary": "",
                    "employment_type": "",
                    "url": _absolute_url("linkedin_jobs_uk", href),
                }
            )
    return results


def _parse_indeed_detail(html: str) -> dict[str, str]:
    return {
        "description": _strip_html(
            _extract_first(html, r'<div id="jobDescriptionText"[^>]*>(.*?)</div>', re.S)
        ),
        "employment_type": _strip_html(
            _extract_first(
                html,
                (
                    r'data-testid="jobsearch-JobMetadataHeader-item">'
                    r"(Permanent|Contract|Temporary|Part-time)</span>"
                ),
                re.I,
            )
        ),
        "salary": _strip_html(
            _extract_first(html, r'data-testid="salaryInfoAndJobType">(.*?)<', re.S)
        ),
    }


def _parse_totaljobs_detail(html: str) -> dict[str, str]:
    return {
        "description": _strip_html(
            _extract_first(html, r'<div class="job-description"[^>]*>(.*?)</div>', re.S)
        ),
        "employment_type": _strip_html(
            _extract_first(html, r'<span class="job-type"[^>]*>(.*?)<', re.S)
        ),
        "salary": _strip_html(
            _extract_first(html, r'<span class="job-salary"[^>]*>(.*?)<', re.S)
        ),
    }


def _parse_linkedin_detail(html: str) -> dict[str, str]:
    return {
        "description": _strip_html(
            _extract_first(
                html, r'<div class="show-more-less-html__markup"[^>]*>(.*?)</div>', re.S
            )
        ),
        "employment_type": _strip_html(
            _extract_first(html, r"Employment type</h3>\s*<span[^>]*>(.*?)<", re.S)
        ),
        "salary": _strip_html(
            _extract_first(html, r"Salary</h3>\s*<span[^>]*>(.*?)<", re.S)
        ),
    }


def _extract_first(text: str, pattern: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    if not match:
        return ""
    return match.group(1).strip()


def _strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    cleaned = re.sub(r"\s+", " ", without_tags)
    return cleaned.strip()


def _absolute_url(source: str, url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urllib.parse.urljoin(_SOURCE_HOSTS[source], url)
