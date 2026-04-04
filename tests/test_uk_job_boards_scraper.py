from __future__ import annotations

import urllib.parse

import pytest

from sponsor_sync.connectors.base import JobQuery
from sponsor_sync.connectors.uk_job_boards_scraper import UkJobBoardsScraperConnector

INDEED_LIST_HTML = """
<div class="job_seen_beacon" data-jk="indeed-101">
  <h2><a href="/viewjob?jk=indeed-101" title="Senior Software Engineer"></a></h2>
  <span data-testid="company-name">Acme Ltd</span>
  <div data-testid="text-location">London, England</div>
  <div data-testid="attribute_snippet_testid">£60,000 - £75,000 a year</div>
</div>
</div>
"""

INDEED_DETAIL_HTML = """
<div id="jobDescriptionText">Build distributed systems.</div>
<span data-testid="jobsearch-JobMetadataHeader-item">Permanent</span>
<div data-testid="salaryInfoAndJobType">£60,000 - £75,000 a year</div>
"""

TOTALJOBS_LIST_HTML = """
<article class="job" data-job-id="tj-202">
  <a class="job-title" href="/job/principal-engineer/tj-202">Principal Engineer</a>
  <span class="company">Beta Tech</span>
  <span class="location">Manchester</span>
  <span class="salary">£70,000 per annum</span>
  <span class="contract">Permanent</span>
</article>
"""

TOTALJOBS_DETAIL_HTML = """
<div class="job-description">Lead architecture for platform services.</div>
<span class="job-type">Permanent</span>
<span class="job-salary">£70,000 per annum</span>
"""

LINKEDIN_LIST_HTML = """
<li data-occludable-job-id="li-303">
  <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/li-303"></a>
  <h3 class="base-search-card__title">Tech Lead</h3>
  <h4 class="base-search-card__subtitle">Gamma Systems</h4>
  <span class="job-search-card__location">Bristol, England, United Kingdom</span>
</li>
"""

LINKEDIN_DETAIL_HTML = """
<div class="show-more-less-html__markup">Own technical strategy and delivery.</div>
<h3>Employment type</h3><span>Permanent</span>
<h3>Salary</h3><span>£82,000 per year</span>
"""


def test_scraper_connector_parses_list_and_detail_pages_for_all_supported_sources(
) -> None:
    pages = {
        (
            "https://uk.indeed.com/jobs?keywords=engineer&location=London"
        ): INDEED_LIST_HTML,
        "https://uk.indeed.com/viewjob?jk=indeed-101": INDEED_DETAIL_HTML,
        (
            "https://www.totaljobs.com/jobs?keywords=engineer&location=London"
        ): TOTALJOBS_LIST_HTML,
        (
            "https://www.totaljobs.com/job/principal-engineer/tj-202"
        ): TOTALJOBS_DETAIL_HTML,
        (
            "https://www.linkedin.com/jobs/search?keywords=engineer&location=London"
        ): LINKEDIN_LIST_HTML,
        "https://www.linkedin.com/jobs/view/li-303": LINKEDIN_DETAIL_HTML,
    }

    def fake_fetcher(url: str) -> str:
        decoded_url = urllib.parse.unquote_plus(url)
        return pages[decoded_url]

    connector = UkJobBoardsScraperConnector(page_fetcher=fake_fetcher)

    jobs = connector.fetch_jobs(JobQuery(keywords="engineer", location="London"))

    assert len(jobs) == 3
    assert {job.source for job in jobs} == {
        "indeed_uk",
        "totaljobs_uk",
        "linkedin_jobs_uk",
    }
    assert all(job.is_permanent for job in jobs)
    assert all(job.passes_salary_threshold for job in jobs)


def test_scraper_connector_enforces_uk_only_location_queries() -> None:
    connector = UkJobBoardsScraperConnector(page_fetcher=lambda _url: "")

    with pytest.raises(ValueError, match="UK locations only"):
        connector.fetch_jobs(JobQuery(keywords="engineer", location="Berlin, Germany"))
