# Job Search System Implementation Plan (CV-Driven, Multi-Source)

## 1) Goal
Build a system that ingests a candidate CV, searches multiple job sources (APIs + web scraping), and returns high-fit **permanent** roles in the UK market that match these target titles:

- Senior Software Engineer
- Tech Lead
- Principal Engineer
- Principal Developer

With mandatory filters:

- Salary > **£45,000 GBP**
- Employment type: **Permanent only**
- Exclude irrelevant/undesired roles using configurable negative filters

The system will use the **Claude API** for CV understanding, semantic relevance scoring, and ranking explanations.

---

## 2) Scope and Non-Goals

### In Scope
- CV parsing and structured profile extraction
- Source connectors for API-based and scrape-based job sites
- Title + salary + contract-type filtering
- Deduplication and normalization across sources
- Claude-powered relevance scoring
- Output ranking + export (JSON/CSV)
- Scheduling for periodic runs

### Out of Scope (v1)
- One-click job application automation
- End-to-end browser automation for captcha-protected flows
- Full historical salary intelligence beyond listed salary fields

---

## 3) High-Level Architecture

1. **Input Layer**
   - CV upload (PDF/DOCX/TXT)
   - Optional user preferences (location, remote/hybrid, must-have skills)

2. **Profile Extraction Layer**
   - Text extraction from CV
   - Claude prompt to produce structured candidate profile:
     - Core skills
     - Seniority indicators
     - Domain expertise
     - Preferred roles

3. **Source Acquisition Layer**
   - **API Connectors**: query sources with keyword/title/location filters
   - **Scraper Connectors**: pull listings where APIs unavailable (respect robots.txt and TOS)

4. **Normalization Layer**
   - Map heterogeneous source fields into a common schema
   - Parse salary into numeric annual GBP range
   - Standardize employment type labels (perm/full-time/etc.)

5. **Rules & Filters Layer**
   - Title filter (allowed role patterns)
   - Salary threshold (> 45000 GBP)
   - Permanent-only filter
   - Exclusion filters (keywords/companies/contracts)

6. **AI Relevance Layer (Claude API)**
   - Score CV-to-job fit (0–100)
   - Generate concise rationale per match

7. **Ranking & Output Layer**
   - Final weighted ranking: rules + semantic score + freshness
   - Exports + optional notifications

---

## 4) Data Model (Canonical Job Schema)

```yaml
job_id: string
source: string
source_job_id: string
title: string
company: string
location: string
employment_type: string       # permanent/contract/etc.
salary_min_gbp: number|null
salary_max_gbp: number|null
salary_currency: string|null
salary_period: string|null    # annual/monthly/daily/hourly
description: string
posted_at: datetime|null
url: string
scraped_at: datetime
normalized_title: string
is_permanent: boolean
passes_salary_threshold: boolean
fit_score: number|null
fit_reason: string|null
```

---

## 5) Filtering Logic (Deterministic)

### 5.1 Allowed Titles (case-insensitive, regex/semantic)
- `senior software engineer`
- `tech lead`
- `principal engineer`
- `principal developer`

Also support light variants (e.g., `lead software engineer`) via synonym map.

### 5.2 Salary Rule
- Pass if:
  - `salary_min_gbp > 45000`, or
  - `salary_max_gbp > 45000`, or
  - parsed single salary value > 45000
- If salary missing:
  - mark as `salary_unknown`
  - include in optional “manual review” bucket (configurable)

### 5.3 Contract Type Rule
- Include only permanent indicators:
  - `permanent`, `full-time permanent`
- Exclude:
  - `contract`, `freelance`, `temporary`, `internship`, `part-time` (unless explicitly allowed later)

### 5.4 Exclusion Rules
Config-driven blocks for:
- Keywords in title/description (e.g., unrelated domains)
- Company blacklist
- Required on-site-only (optional preference-based)

---

## 6) Claude API Integration Design

### 6.1 Use Cases
1. **CV Structuring**: Convert raw CV text into machine-readable profile JSON.
2. **Fit Scoring**: Evaluate candidate-job relevance and provide short reason.

### 6.2 Prompt Strategy
- Use strict JSON schema output in prompts.
- Include deterministic instruction hierarchy:
  - prioritize relevant engineering leadership/senior IC matches
  - penalize non-permanent roles or mismatched domains
- Keep temperature low for consistency.

### 6.3 Reliability Controls
- JSON schema validation + retry on malformed responses
- Timeouts + backoff retries
- Token/cost guardrails per run

---

## 7) Connector Strategy (API + Scraping)

### API Sources
- Build one connector module per provider:
  - auth handling
  - pagination
  - rate-limiting
  - response-to-schema mapping

### Scraping Sources
- Use polite scraping practices:
  - robots.txt awareness
  - request throttling
  - user-agent rotation only if compliant with TOS
- Parser tests for each source HTML structure
- Fallback selector strategies when layout changes

---

## 8) Pipeline Execution Flow

1. Load configuration (titles, salary threshold, exclusions).
2. Parse CV and build candidate profile with Claude.
3. Fetch jobs from APIs.
4. Fetch jobs from scraper connectors.
5. Normalize all jobs to canonical schema.
6. Apply hard filters (title, salary, permanent, exclusions).
7. Deduplicate by URL + title/company similarity hash.
8. Score remaining jobs with Claude fit scoring.
9. Rank and export results.
10. Persist run metrics + logs.

---

## 9) Tech Stack Recommendation

- **Language**: Python 3.11+
- **API Layer**: FastAPI (optional service wrapper)
- **Scheduling**: APScheduler/Cron
- **Storage**: SQLite/PostgreSQL (jobs + run logs)
- **Scraping**: httpx + BeautifulSoup (or Playwright when necessary)
- **Validation**: Pydantic
- **Testing**: pytest

---

## 10) Milestone Plan

### Phase 1: Foundation (Week 1)
- Project skeleton
- Canonical schema + config system
- CV text extraction
- Claude CV profile extraction

### Phase 2: Source Integrations (Week 2)
- Implement 2 API connectors
- Implement 1 scraper connector
- Normalization + base filtering

### Phase 3: Ranking & Output (Week 3)
- Claude fit scoring
- Dedupe + ranking engine
- JSON/CSV export + CLI command

### Phase 4: Hardening (Week 4)
- Observability, retries, error handling
- Unit/integration tests
- Documentation + deployment scripts

---

## 11) Quality & Testing Strategy

- Unit tests:
  - salary parser
  - title normalization
  - permanent classifier
  - exclusion filters
- Integration tests:
  - connector contract tests
  - end-to-end pipeline with fixture data
- Regression tests for scraper selectors
- Prompt output schema tests for Claude responses

---

## 12) Observability and Operations

- Structured logging per pipeline stage
- Run metrics:
  - total fetched
  - filtered out by rule type
  - final shortlisted
  - average fit score
- Alerting on connector failures and zero-result anomalies

---

## 13) Security and Secrets Handling

- Store API keys in environment variables or secret manager.
- Never hardcode secrets in code or commit them to git.
- Rotate any exposed keys immediately.
- Mask secrets in logs and error traces.

---

## 14) Deliverables

- `IMPLEMENTATION_PLAN.md` (this document)
- Config template for filters and thresholds
- Initial pipeline scaffold
- Connector interface definitions
- Test harness and sample fixtures

---

## 15) Immediate Next Steps

1. Confirm initial target sources (which APIs + websites).
2. Finalize exclusion list semantics.
3. Create config-driven rules file.
4. Implement CV parser + Claude profile extraction module.
5. Build first API connector and run dry pipeline test.
