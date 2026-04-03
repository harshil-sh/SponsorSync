"""Reed.co.uk Jobseeker API connector implementation."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone

from sponsor_sync.connectors.base import (
    BaseConnector,
    JobQuery,
    RateLimiter,
    retry_operation,
)
from sponsor_sync.models import JobPosting
from sponsor_sync.utilities import normalize_contract_type, normalize_title

REED_API_BASE_URL = "https://www.reed.co.uk/api/1.0/search"


class ReedApiConnector(BaseConnector):
    """Fetch and normalize jobs from the Reed Jobseeker API."""

    source_name = "reed"

    def __init__(
        self,
        api_key: str,
        *,
        page_size: int = 100,
        min_request_interval_seconds: float = 0.1,
        request_timeout_seconds: float = 15.0,
        request_executor: (
            Callable[[urllib.request.Request, float], bytes] | None
        ) = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Reed API key is required")
        if page_size < 1 or page_size > 100:
            raise ValueError("page_size must be between 1 and 100")

        self._api_key = api_key
        self._page_size = page_size
        self._request_timeout_seconds = request_timeout_seconds
        self._request_executor = request_executor or self._default_request_executor
        self._rate_limiter = RateLimiter(min_request_interval_seconds)

    def fetch_jobs(self, query: JobQuery) -> list[JobPosting]:
        """Fetch all pages for a query and map results into canonical job postings."""
        results: list[JobPosting] = []
        offset = 0

        while True:
            payload = self._search_once(query=query, results_to_skip=offset)
            jobs = payload.get("results", [])
            if not jobs:
                break

            results.extend(self._map_job(item) for item in jobs)
            if len(jobs) < self._page_size:
                break

            offset += self._page_size

        return results

    def _search_once(self, query: JobQuery, results_to_skip: int) -> dict[str, object]:
        params = {
            "keywords": query.keywords,
            "locationName": query.location,
            "resultsToTake": str(min(query.page_size, self._page_size)),
            "resultsToSkip": str(results_to_skip),
        }
        url = f"{REED_API_BASE_URL}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(url, headers=self._auth_headers())

        self._rate_limiter.wait()

        raw_bytes = retry_operation(
            lambda: self._request_executor(request, self._request_timeout_seconds),
            retryable_exceptions=(
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
            ),
            attempts=3,
            backoff_seconds=0.25,
        )
        parsed = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Reed API returned a non-object response")
        return parsed

    def _auth_headers(self) -> dict[str, str]:
        token = base64.b64encode(f"{self._api_key}:".encode()).decode("ascii")
        return {
            "Accept": "application/json",
            "Authorization": f"Basic {token}",
        }

    @staticmethod
    def _default_request_executor(
        request: urllib.request.Request, timeout_seconds: float
    ) -> bytes:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    @staticmethod
    def _map_job(raw_job: object) -> JobPosting:
        if not isinstance(raw_job, dict):
            raise ValueError("Unexpected job payload from Reed API")

        source_job_id = str(raw_job.get("jobId", "")).strip()
        title = str(raw_job.get("jobTitle", "")).strip()
        company = str(raw_job.get("employerName", "Unknown employer")).strip()
        location = str(raw_job.get("locationName", "Unknown location")).strip()
        description = str(
            raw_job.get("jobDescription", "No description provided")
        ).strip()
        job_url = str(raw_job.get("jobUrl", "")).strip()
        date_text = str(raw_job.get("date", "")).strip()

        posted_at: datetime | None = None
        if date_text:
            posted_at = datetime.fromisoformat(date_text.replace("Z", "+00:00"))

        employment_type = normalize_contract_type(raw_job.get("employmentTypeName"))
        salary_min = _to_float(raw_job.get("minimumSalary"))
        salary_max = _to_float(raw_job.get("maximumSalary"))

        threshold = 45000.0
        passes_salary_threshold = bool(
            (salary_min is not None and salary_min > threshold)
            or (salary_max is not None and salary_max > threshold)
        )

        return JobPosting(
            job_id=f"reed:{source_job_id}",
            source="reed",
            source_job_id=source_job_id,
            title=title,
            company=company,
            location=location,
            employment_type=employment_type,
            salary_min_gbp=salary_min,
            salary_max_gbp=salary_max,
            salary_currency="GBP",
            salary_period="annual",
            description=description,
            posted_at=posted_at,
            url=job_url,
            scraped_at=datetime.now(timezone.utc),
            normalized_title=normalize_title(title),
            is_permanent=employment_type == "permanent",
            passes_salary_threshold=passes_salary_threshold,
        )


def _to_float(value: object) -> float | None:
    if value is None or value == "":
        return None

    return float(value)
