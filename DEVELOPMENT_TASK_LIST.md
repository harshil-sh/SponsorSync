# Development Task List — CV-Driven Multi-Source Job Search System

This task list turns the implementation plan into an execution backlog the team can complete end-to-end.

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Done

---

## Epic 0: Project Setup & Governance

### 0.1 Repository and environment bootstrap
- [ ] Create Python package structure (`src/`, `tests/`, `scripts/`, `configs/`)
- [ ] Add `.env.example` with non-secret placeholders
- [ ] Add dependency management (`pyproject.toml`)
- [ ] Add lint/format config (ruff/black)
- [ ] Add pre-commit hooks

**Definition of Done (DoD)**
- `pip install -e .` works
- `pytest` discovers test suite
- `ruff check .` and `black --check .` pass

### 0.2 Security baseline
- [ ] Add secrets policy to README (never commit API keys)
- [ ] Add `.gitignore` rules for `.env`, credentials, exported data
- [ ] Add basic secret scanning step in CI

**DoD**
- CI fails if obvious secrets are committed

---

## Epic 1: Config, Domain Models, and Core Utilities

### 1.1 Config system
- [ ] Implement strongly typed app config (Pydantic settings)
- [ ] Add rules config file (titles, salary threshold, exclusions)
- [ ] Support environment-specific overrides

**DoD**
- App starts with defaults and env overrides
- Invalid config fails with clear errors

### 1.2 Canonical job schema
- [ ] Implement canonical `JobPosting` model
- [ ] Implement run metadata model (`RunMetrics`, `RunSummary`)
- [ ] Add serializer/deserializer helpers

**DoD**
- All connectors emit canonical model
- Schema validation tested

### 1.3 Utility modules
- [ ] Salary parsing utility (annualize salary in GBP)
- [ ] Contract-type normalization utility
- [ ] Title normalization + synonym expansion

**DoD**
- Utility unit tests cover expected UK salary formats and edge cases

---

## Epic 2: CV Ingestion and Profile Extraction (Claude)

### 2.1 CV ingestion pipeline
- [ ] Implement CV file loader (PDF/DOCX/TXT)
- [ ] Add text extraction adapters with fallback order
- [ ] Add basic cleaning and section segmentation

**DoD**
- Sample CV fixtures parse into clean text

### 2.2 Claude profile extraction
- [ ] Implement Claude client wrapper
- [ ] Create CV→Profile prompt template with strict JSON output
- [ ] Add schema validation + retry policy for malformed responses

**DoD**
- `extract_candidate_profile(cv_text)` returns validated structured profile

### 2.3 Token/cost controls
- [ ] Add max tokens per call safeguards
- [ ] Add per-run budget guardrails
- [ ] Add logging for prompt/response metadata (redacted)

**DoD**
- Exceeding configured budget fails gracefully with actionable error

---

## Epic 3: Source Connectors (APIs)

### 3.1 Connector framework
- [ ] Define `BaseConnector` interface (`fetch_jobs(query) -> list[JobPosting]`)
- [ ] Add shared pagination, retry, rate-limit helpers

**DoD**
- New connectors can be added with minimal boilerplate

### 3.2 API connector #1
- [ ] Implement authentication and request signing if required
- [ ] Add pagination + mapping to canonical schema
- [ ] Add connector integration tests with mocked responses

### 3.3 API connector #2
- [ ] Implement second API connector similarly
- [ ] Add mapping parity tests (field-level assertions)

**DoD**
- Both API connectors produce validated canonical objects

---

## Epic 4: Source Connectors (Web Scraping)

### 4.1 Scraper framework
- [ ] Define scraper connector interface
- [ ] Add throttling and backoff utility
- [ ] Add robots/TOS compliance checklist per source

### 4.2 Scraper connector #1
- [ ] Build parser selectors for list + details pages
- [ ] Normalize extracted fields to canonical schema
- [ ] Add fixture-based parser tests

### 4.3 Scraper resilience
- [ ] Add fallback selectors / heuristic extraction
- [ ] Add selector break detection alerting

**DoD**
- Scraper can run repeatedly without breaking on minor DOM changes

---

## Epic 5: Deterministic Filtering and Exclusions

### 5.1 Title filtering
- [ ] Implement allowlist matching for required roles
- [ ] Add synonyms/variants map

### 5.2 Salary threshold filter
- [ ] Enforce `> 45000 GBP`
- [ ] Handle missing salary as configurable behavior (`exclude` or `manual_review`)

### 5.3 Employment type filter
- [ ] Allow permanent-only
- [ ] Exclude contract/freelance/temp/internship/part-time by default

### 5.4 Exclusion rules
- [ ] Implement keyword exclusion lists
- [ ] Implement company blacklist
- [ ] Implement optional location-mode exclusions

**DoD**
- Filter reason codes are emitted for every excluded job

---

## Epic 6: Deduplication, Scoring, and Ranking

### 6.1 Deduplication
- [ ] Implement deterministic hash key (`source_job_id/url/title+company`)
- [ ] Implement fuzzy duplicate fallback

### 6.2 Claude fit scoring
- [ ] Implement CV-profile + job scoring prompt
- [ ] Return score (0–100) + short explanation
- [ ] Add schema validation and retry controls

### 6.3 Ranking engine
- [ ] Define weighted ranking formula (hard filters + fit + recency)
- [ ] Add tie-breaker logic

**DoD**
- Ranked list is reproducible with same inputs/config

---

## Epic 7: Outputs, Storage, and Interfaces

### 7.1 Output exports
- [ ] JSON export of shortlisted jobs
- [ ] CSV export for manual review
- [ ] Optional markdown summary report

### 7.2 Persistence
- [ ] Add SQLite/PostgreSQL storage adapter
- [ ] Persist run summary and filtered counts by reason

### 7.3 Interface layer
- [ ] CLI command for full pipeline run
- [ ] Optional FastAPI endpoint for triggering/searching runs

**DoD**
- User can execute one command and retrieve ranked results + metrics

---

## Epic 8: Scheduling, Monitoring, and Alerts

### 8.1 Scheduling
- [ ] Add cron/APScheduler job to run pipeline periodically
- [ ] Add lock to prevent overlapping runs

### 8.2 Monitoring
- [ ] Add structured logs per stage
- [ ] Add metrics counters (fetched/filtered/shortlisted/errors)

### 8.3 Alerting
- [ ] Alert on connector failures
- [ ] Alert on suspiciously low result counts

**DoD**
- Operational dashboards/logs clearly show run health

---

## Epic 9: Testing & Quality Gates

### 9.1 Unit tests
- [ ] Salary parser tests (UK formats, ranges, malformed)
- [ ] Title normalization and role matching tests
- [ ] Contract and exclusion rule tests

### 9.2 Integration tests
- [ ] End-to-end test with fixtures and mocked connectors
- [ ] Connector contract tests for each source

### 9.3 CI pipeline
- [ ] Add CI for lint + tests + secret scan
- [ ] Add coverage threshold gate

**DoD**
- CI is green and blocks regressions before merge

---

## Epic 10: Documentation & Handover

### 10.1 Developer docs
- [ ] Architecture diagram + component responsibilities
- [ ] Connector implementation guide
- [ ] Prompt and schema versioning guide

### 10.2 Operator docs
- [ ] Runbook for scheduled jobs
- [ ] Incident handling steps (failing connector, zero results, budget exceeded)

### 10.3 Product docs
- [ ] User instructions for CV upload/search configuration
- [ ] Explanation of scoring and ranking transparency

**DoD**
- New engineer can set up and run the system from docs only

---

## Suggested Delivery Sequence

1. Epic 0 → Epic 1 (foundation)
2. Epic 2 (CV + Claude extraction)
3. Epic 3 + Epic 4 (data acquisition)
4. Epic 5 + Epic 6 (quality of matching)
5. Epic 7 + Epic 8 (usability + operations)
6. Epic 9 + Epic 10 (hardening + handover)

---

## Immediate Sprint Backlog (Recommended)

- [ ] Implement config + canonical schema + salary parser
- [ ] Build CV extraction and Claude profile module
- [ ] Implement first API connector end-to-end
- [ ] Implement hard filters (title/salary/permanent/exclusions)
- [ ] Produce first ranked output (JSON) from a dry run
