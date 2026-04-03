from __future__ import annotations

import importlib.util
from datetime import datetime, timezone

import pytest

HAS_PYDANTIC = importlib.util.find_spec("pydantic") is not None
pytestmark = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic is not installed")

if HAS_PYDANTIC:
    from pydantic import ValidationError

    from sponsor_sync.models import (
        JobPosting,
        RunMetrics,
        RunSummary,
        deserialize_job_posting,
        deserialize_run_summary,
        serialize_job_posting,
        serialize_run_summary,
    )


def _example_job_payload() -> dict[str, object]:
    return {
        "job_id": "job-123",
        "source": "example_api",
        "source_job_id": "source-987",
        "title": "Senior Software Engineer",
        "company": "Acme Tech",
        "location": "London, UK",
        "employment_type": "permanent",
        "salary_min_gbp": 70000,
        "salary_max_gbp": 90000,
        "salary_currency": "GBP",
        "salary_period": "annual",
        "description": "Build and operate distributed systems.",
        "posted_at": "2026-03-30T09:00:00+00:00",
        "url": "https://jobs.example.com/roles/123",
        "scraped_at": "2026-04-03T10:00:00+00:00",
        "normalized_title": "senior software engineer",
        "is_permanent": True,
        "passes_salary_threshold": True,
        "fit_score": 92,
        "fit_reason": "Strong backend leadership match.",
    }


def test_job_posting_schema_validation_and_round_trip_serialization() -> None:
    parsed = deserialize_job_posting(_example_job_payload())
    assert isinstance(parsed, JobPosting)

    serialized = serialize_job_posting(parsed)
    assert serialized["posted_at"] == "2026-03-30T09:00:00Z"
    assert serialized["url"] == "https://jobs.example.com/roles/123"


def test_job_posting_rejects_invalid_payload() -> None:
    payload = _example_job_payload()
    payload["job_id"] = ""
    payload["salary_min_gbp"] = -100

    with pytest.raises(ValidationError):
        deserialize_job_posting(payload)


def test_run_summary_schema_and_serialization_helpers() -> None:
    job = JobPosting.model_validate(_example_job_payload())
    metrics = RunMetrics(
        run_id="run-001",
        started_at=datetime(2026, 4, 3, 9, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 4, 3, 10, 0, tzinfo=timezone.utc),
        fetched_count=120,
        normalized_count=110,
        filtered_count=80,
        shortlisted_count=30,
        error_count=1,
    )
    summary = RunSummary(
        metrics=metrics,
        shortlisted_jobs=[job],
        filter_reason_counts={"employment_type_excluded": 18, "title_mismatch": 42},
    )

    serialized = serialize_run_summary(summary)
    reparsed = deserialize_run_summary(serialized)

    assert reparsed.metrics.run_id == "run-001"
    assert reparsed.shortlisted_jobs[0].job_id == "job-123"
    assert reparsed.filter_reason_counts["title_mismatch"] == 42
