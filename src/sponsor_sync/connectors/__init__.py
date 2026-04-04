"""Source connector implementations and shared contracts."""

from sponsor_sync.connectors.base import BaseConnector, JobQuery
from sponsor_sync.connectors.reed import ReedApiConnector
from sponsor_sync.connectors.uk_job_boards_scraper import UkJobBoardsScraperConnector
from sponsor_sync.connectors.scraper_framework import (
    BaseScraperConnector,
    ScraperComplianceChecklist,
    ScraperRequestController,
    build_scraper_compliance_checklist,
)

__all__ = [
    "BaseConnector",
    "JobQuery",
    "ReedApiConnector",
    "UkJobBoardsScraperConnector",
    "BaseScraperConnector",
    "ScraperComplianceChecklist",
    "ScraperRequestController",
    "build_scraper_compliance_checklist",
]
