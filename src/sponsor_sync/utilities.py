"""Utility helpers for salary parsing and deterministic normalization rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

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

_HOURS_PER_YEAR = 40 * 52
_DAYS_PER_YEAR = 5 * 52


@dataclass(frozen=True)
class AnnualSalaryRange:
    """Parsed annual salary range represented in GBP."""

    minimum_gbp: float | None
    maximum_gbp: float | None


def _annualization_multiplier(salary_text: str) -> float:
    lowered = salary_text.lower()
    if any(token in lowered for token in ("per hour", "/hour", "hourly", " an hour")):
        return float(_HOURS_PER_YEAR)
    if any(token in lowered for token in ("per day", "/day", "daily")):
        return float(_DAYS_PER_YEAR)
    if any(token in lowered for token in ("per week", "/week", "weekly", "pw")):
        return 52.0
    if any(token in lowered for token in ("per month", "/month", "monthly", "pcm")):
        return 12.0
    return 1.0


def _extract_salary_amounts(salary_text: str) -> list[float]:
    pattern = re.compile(r"(?:£|gbp\s*)?\s*(\d[\d,]*(?:\.\d+)?)\s*([kK])?")
    amounts: list[float] = []
    contains_gbp_hint = bool(re.search(r"£|\bgbp\b", salary_text, flags=re.IGNORECASE))

    for matched in pattern.finditer(salary_text):
        number_text = matched.group(1)
        has_k = bool(matched.group(2))
        value = float(number_text.replace(",", ""))

        if has_k:
            value *= 1000

        if contains_gbp_hint or has_k or value >= 1000:
            amounts.append(value)

    return amounts


def parse_salary_to_annual_gbp(salary_text: str) -> AnnualSalaryRange:
    """Parse UK salary text and return annualized GBP min/max values when possible."""
    lowered = salary_text.lower()
    if any(symbol in lowered for symbol in ("$", "€")):
        return AnnualSalaryRange(minimum_gbp=None, maximum_gbp=None)

    amounts = _extract_salary_amounts(salary_text)
    if not amounts:
        return AnnualSalaryRange(minimum_gbp=None, maximum_gbp=None)

    multiplier = _annualization_multiplier(salary_text)
    annualized = [amount * multiplier for amount in amounts[:2]]

    if len(annualized) == 1:
        return AnnualSalaryRange(minimum_gbp=annualized[0], maximum_gbp=annualized[0])

    return AnnualSalaryRange(
        minimum_gbp=min(annualized),
        maximum_gbp=max(annualized),
    )


def normalize_contract_type(contract_text: str | None) -> EmploymentType:
    """Normalize heterogeneous employment labels to canonical values."""
    if not contract_text:
        return "unknown"

    lowered = contract_text.strip().lower()
    if "intern" in lowered:
        return "internship"
    if any(
        token in lowered for token in ("freelance", "self-employed", "self employed")
    ):
        return "freelance"
    if any(token in lowered for token in ("temporary", "temp")):
        return "temporary"
    if "contract" in lowered:
        return "contract"
    if "part-time" in lowered or "part time" in lowered:
        return "part_time"
    if "permanent" in lowered:
        return "permanent"
    if "full-time" in lowered or "full time" in lowered:
        return "full_time"

    return "unknown"


def normalize_title(raw_title: str) -> str:
    """Normalize title casing and punctuation for matching."""
    collapsed = re.sub(r"[^a-z0-9]+", " ", raw_title.lower())
    return re.sub(r"\s+", " ", collapsed).strip()


_TITLE_SYNONYMS: dict[str, set[str]] = {
    "senior software engineer": {
        "lead software engineer",
        "senior software developer",
        "sr software engineer",
    },
    "tech lead": {
        "technical lead",
        "engineering lead",
        "lead engineer",
    },
    "principal engineer": {
        "principal software engineer",
        "lead principal engineer",
    },
    "principal developer": {
        "principal software developer",
        "lead developer",
    },
}


def expand_title_synonyms(title: str) -> set[str]:
    """Return normalized title plus known synonym variants."""
    normalized = normalize_title(title)

    for canonical, variants in _TITLE_SYNONYMS.items():
        normalized_variants = {normalize_title(value) for value in variants}
        if normalized == canonical or normalized in normalized_variants:
            return {canonical, *normalized_variants}

    return {normalized}
