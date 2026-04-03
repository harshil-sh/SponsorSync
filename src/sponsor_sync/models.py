"""Canonical domain models for normalized job data and pipeline run metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

EmploymentType = Literal[
    "permanent",
    "contract",
    "freelance",
    "temporary",
    "internship",
    "part_time",
    "full_time",
    "unknown",
]
SalaryPeriod = Literal["annual", "monthly", "daily", "hourly"]


class JobPosting(BaseModel):
    """Canonical representation of a job listing emitted by any connector."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_job_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    location: str = Field(min_length=1)
    employment_type: EmploymentType
    salary_min_gbp: float | None = Field(default=None, ge=0)
    salary_max_gbp: float | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, min_length=1)
    salary_period: SalaryPeriod | None = None
    description: str = Field(min_length=1)
    posted_at: datetime | None = None
    url: HttpUrl
    scraped_at: datetime
    normalized_title: str = Field(min_length=1)
    is_permanent: bool
    passes_salary_threshold: bool
    fit_score: float | None = Field(default=None, ge=0, le=100)
    fit_reason: str | None = None


class RunMetrics(BaseModel):
    """Counts and timing information collected for a single pipeline run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime | None = None
    fetched_count: int = Field(default=0, ge=0)
    normalized_count: int = Field(default=0, ge=0)
    filtered_count: int = Field(default=0, ge=0)
    shortlisted_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)


class RunSummary(BaseModel):
    """Top-level run artifact for monitoring and downstream reporting."""

    model_config = ConfigDict(extra="forbid")

    metrics: RunMetrics
    shortlisted_jobs: list[JobPosting] = Field(default_factory=list)
    filter_reason_counts: dict[str, int] = Field(default_factory=dict)


def serialize_job_posting(job: JobPosting) -> dict[str, Any]:
    """Serialize a canonical job posting to a JSON-safe dictionary."""

    return job.model_dump(mode="json")


def deserialize_job_posting(payload: dict[str, Any]) -> JobPosting:
    """Deserialize untrusted data into a validated canonical job posting."""

    return JobPosting.model_validate(payload)


def serialize_run_summary(summary: RunSummary) -> dict[str, Any]:
    """Serialize run summary data to a JSON-safe dictionary."""

    return summary.model_dump(mode="json")


def deserialize_run_summary(payload: dict[str, Any]) -> RunSummary:
    """Deserialize untrusted data into a validated run summary."""

    return RunSummary.model_validate(payload)
