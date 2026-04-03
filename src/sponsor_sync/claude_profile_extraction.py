"""Claude-powered candidate profile extraction from CV text."""

from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any
from urllib import error, request

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


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
    timeout_seconds: int = 30
    max_retries: int = 2

    def extract_candidate_profile(self, cv_text: str) -> CandidateProfile:
        """Extract a validated candidate profile from CV text via Claude."""

        if not cv_text.strip():
            raise ValueError("cv_text must not be empty")

        prompt = build_cv_profile_prompt(cv_text)
        last_error: Exception | None = None

        for _attempt in range(self.max_retries + 1):
            response_body = self._post_messages(prompt)
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
