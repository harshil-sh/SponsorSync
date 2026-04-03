"""Claude-powered candidate profile extraction from CV text."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any
from urllib import error, request

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
LOGGER = logging.getLogger(__name__)


class ClaudeBudgetExceededError(RuntimeError):
    """Raised when a Claude run exceeds configured token/cost budget."""


@dataclass
class ClaudeRunUsage:
    """Per-run usage counters for token and cost guardrails."""

    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class CandidateProfile(BaseModel):
    """Structured profile derived from a raw CV."""

    model_config = ConfigDict(extra="forbid")

    core_skills: list[str] = Field(min_length=1)
    seniority_indicators: list[str] = Field(min_length=1)
    domain_expertise: list[str] = Field(min_length=1)
    preferred_roles: list[str] = Field(min_length=1)


@dataclass(frozen=True)
class ClaudeClient:
    """Minimal Anthropic Claude API wrapper focused on profile extraction."""

    api_key: str
    model: str = "claude-3-5-sonnet-latest"
    max_tokens: int = 800
    max_tokens_limit: int = 4096
    timeout_seconds: int = 30
    max_retries: int = 2
    run_budget_usd: float = 1.0
    input_cost_per_million_tokens: float = 3.0
    output_cost_per_million_tokens: float = 15.0
    run_usage: ClaudeRunUsage = field(default_factory=ClaudeRunUsage)

    def extract_candidate_profile(self, cv_text: str) -> CandidateProfile:
        """Extract a validated candidate profile from CV text via Claude."""

        if not cv_text.strip():
            raise ValueError("cv_text must not be empty")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")
        if self.max_tokens > self.max_tokens_limit:
            raise ValueError(
                "max_tokens exceeds configured per-call limit "
                f"({self.max_tokens_limit})"
            )
        if self.run_budget_usd <= 0:
            raise ValueError("run_budget_usd must be greater than zero")
        self._assert_budget_remaining()

        prompt = build_cv_profile_prompt(cv_text)
        last_error: Exception | None = None

        for _attempt in range(self.max_retries + 1):
            response_body = self._post_messages(prompt)
            self._record_usage(response_body, prompt)
            try:
                raw_text = _extract_message_text(response_body)
                raw_json = _extract_json_payload(raw_text)
                payload = json.loads(raw_json)
                return CandidateProfile.model_validate(payload)
            except (JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc

        raise RuntimeError(
            "Claude returned malformed profile output after retry attempts"
        ) from last_error

    def _assert_budget_remaining(self) -> None:
        usage = self.run_usage
        if usage.estimated_cost_usd >= self.run_budget_usd:
            raise ClaudeBudgetExceededError(
                "Claude run budget exceeded before request: "
                f"spent=${usage.estimated_cost_usd:.6f}, "
                f"budget=${self.run_budget_usd:.6f}. "
                "Increase run_budget_usd or start a new run."
            )

    def _post_messages(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            ANTHROPIC_MESSAGES_URL,
            data=body,
            method="POST",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:  # pragma: no cover - integration/network behavior
            raise RuntimeError("Failed to call Claude API") from exc

    def _record_usage(self, response_body: dict[str, Any], prompt: str) -> None:
        usage_raw = response_body.get("usage")
        if not isinstance(usage_raw, dict):
            usage_raw = {}

        input_tokens = int(usage_raw.get("input_tokens", 0) or 0)
        output_tokens = int(usage_raw.get("output_tokens", 0) or 0)
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million_tokens
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million_tokens
        call_cost = input_cost + output_cost

        usage = self.run_usage
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.estimated_cost_usd += call_cost

        LOGGER.info(
            (
                "Claude profile extraction metadata: model=%s prompt_chars=%s "
                "response_blocks=%s input_tokens=%s output_tokens=%s "
                "call_cost_usd=%.6f run_cost_usd=%.6f"
            ),
            self.model,
            len(prompt),
            len(response_body.get("content", []))
            if isinstance(response_body.get("content"), list)
            else 0,
            input_tokens,
            output_tokens,
            call_cost,
            usage.estimated_cost_usd,
        )

        if usage.estimated_cost_usd > self.run_budget_usd:
            raise ClaudeBudgetExceededError(
                "Claude run budget exceeded after request: "
                f"spent=${usage.estimated_cost_usd:.6f}, "
                f"budget=${self.run_budget_usd:.6f}. "
                "Lower max_tokens, reduce retries, or increase run_budget_usd."
            )


def build_cv_profile_prompt(cv_text: str) -> str:
    """Build strict JSON-only prompt for CV to profile extraction."""

    return (
        "You are a CV parser for UK software engineering roles.\\n"
        "Return ONLY valid JSON with this exact schema and keys:\\n"
        "{\\n"
        '  "core_skills": ["string"],\\n'
        '  "seniority_indicators": ["string"],\\n'
        '  "domain_expertise": ["string"],\\n'
        '  "preferred_roles": ["string"]\\n'
        "}\\n"
        "Rules:\\n"
        "- No markdown fences.\\n"
        "- No additional keys.\\n"
        "- Use concise, deduplicated values.\\n"
        "- Infer preferred roles from evidence in the CV.\\n\\n"
        "CV TEXT:\\n"
        f"{cv_text.strip()}"
    )


def _extract_message_text(response_body: dict[str, Any]) -> str:
    content = response_body.get("content")
    if not isinstance(content, list):
        raise ValueError("Claude response missing content blocks")

    text_parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                text_parts.append(text)

    combined = "\n".join(part for part in text_parts if part.strip()).strip()
    if not combined:
        raise ValueError("Claude response contained no text output")
    return combined


def _extract_json_payload(text: str) -> str:
    if text.strip().startswith("{") and text.strip().endswith("}"):
        return text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in Claude output")
    return text[start : end + 1]
