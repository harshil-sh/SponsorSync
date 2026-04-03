from __future__ import annotations

import base64
import json
import urllib.parse
import urllib.request

import pytest

from sponsor_sync.connectors.base import JobQuery, retry_operation
from sponsor_sync.connectors.reed import ReedApiConnector


def test_reed_connector_fetches_and_maps_paginated_results() -> None:
    requests: list[str] = []

    page_one = {
        "results": [
            {
                "jobId": 101,
                "jobTitle": "Senior Software Engineer",
                "employerName": "Acme Ltd",
                "locationName": "London",
                "minimumSalary": 55000,
                "maximumSalary": 70000,
                "employmentTypeName": "Permanent",
                "jobDescription": "Build APIs",
                "jobUrl": "https://www.reed.co.uk/jobs/senior-software-engineer/101",
                "date": "2026-03-10T09:00:00Z",
            }
        ]
    }
    page_two = {"results": []}

    def fake_request_executor(request: urllib.request.Request, timeout: float) -> bytes:
        del timeout
        requests.append(request.full_url)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(request.full_url).query)

        auth_header = request.headers.get("Authorization")
        assert auth_header is not None
        expected = base64.b64encode(b"test-key:").decode("ascii")
        assert auth_header == f"Basic {expected}"

        if query["resultsToSkip"] == ["0"]:
            return json.dumps(page_one).encode("utf-8")

        return json.dumps(page_two).encode("utf-8")

    connector = ReedApiConnector(
        api_key="test-key",
        page_size=1,
        request_executor=fake_request_executor,
    )

    jobs = connector.fetch_jobs(
        JobQuery(keywords="software", location="London", page_size=1)
    )

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "reed"
    assert job.source_job_id == "101"
    assert job.employment_type == "permanent"
    assert job.is_permanent is True
    assert job.passes_salary_threshold is True
    assert job.normalized_title == "senior software engineer"
    assert len(requests) == 2


def test_reed_connector_retries_transient_failures() -> None:
    attempts = 0

    def flaky_operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary")
        return "ok"

    result = retry_operation(
        flaky_operation,
        attempts=3,
        retryable_exceptions=(TimeoutError,),
        backoff_seconds=0,
    )

    assert result == "ok"
    assert attempts == 3


def test_reed_connector_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        ReedApiConnector(api_key="   ")
