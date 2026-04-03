from __future__ import annotations

import pytest

from sponsor_sync.claude_profile_extraction import (
    CandidateProfile,
    ClaudeClient,
    build_cv_profile_prompt,
)


class StubClaudeClient(ClaudeClient):
    def __init__(self, responses: list[dict[str, object]], **kwargs: object) -> None:
        super().__init__(api_key="test-key", **kwargs)
        self._responses = responses
        self.calls = 0

    def _post_messages(self, prompt: str) -> dict[str, object]:
        self.calls += 1
        assert "Return ONLY valid JSON" in prompt
        return self._responses[self.calls - 1]


def test_build_cv_profile_prompt_includes_schema() -> None:
    prompt = build_cv_profile_prompt("Senior engineer with Python and AWS")

    assert "core_skills" in prompt
    assert "seniority_indicators" in prompt
    assert "preferred_roles" in prompt
    assert "CV TEXT" in prompt


def test_extract_candidate_profile_retries_on_malformed_response() -> None:
    malformed = {"content": [{"type": "text", "text": "not valid json"}]}
    valid_json = (
        '{"core_skills":["Python"],"seniority_indicators":["Tech Lead"],'
        '"domain_expertise":["Fintech"],"preferred_roles":["Principal Engineer"]}'
    )
    valid = {"content": [{"type": "text", "text": valid_json}]}
    client = StubClaudeClient([malformed, valid], max_retries=2)

    profile = client.extract_candidate_profile("Sample CV text")

    assert profile == CandidateProfile(
        core_skills=["Python"],
        seniority_indicators=["Tech Lead"],
        domain_expertise=["Fintech"],
        preferred_roles=["Principal Engineer"],
    )
    assert client.calls == 2


def test_extract_candidate_profile_fails_after_retry_exhausted() -> None:
    invalid_schema = {
        "content": [
            {"type": "text", "text": '{"core_skills": ["Python"]}'}
        ]
    }
    client = StubClaudeClient([invalid_schema, invalid_schema], max_retries=1)

    with pytest.raises(
        RuntimeError, match="Claude returned malformed profile output"
    ):
        client.extract_candidate_profile("Sample CV text")

    assert client.calls == 2


def test_extract_candidate_profile_rejects_empty_input() -> None:
    client = StubClaudeClient([])

    with pytest.raises(ValueError, match="cv_text must not be empty"):
        client.extract_candidate_profile("   ")
