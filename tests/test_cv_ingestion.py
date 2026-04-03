from __future__ import annotations

from pathlib import Path

import pytest

from sponsor_sync import cv_ingestion


@pytest.fixture
def sample_txt_cv(tmp_path: Path) -> Path:
    cv_path = tmp_path / "candidate_cv.txt"
    cv_path.write_text(
        "Professional Summary\n"
        "Senior engineer with distributed systems experience.\n\n"
        "Experience\n"
        "Tech Lead - Example Corp\n"
        "Built platform services.\n\n"
        "Skills\n"
        "Python, FastAPI, AWS\n",
        encoding="utf-8",
    )
    return cv_path


def test_extract_cv_text_for_txt(sample_txt_cv: Path) -> None:
    extracted = cv_ingestion.extract_cv_text(sample_txt_cv)
    assert "Senior engineer" in extracted
    assert "Skills" in extracted


def test_extract_cv_text_uses_fallback_for_docx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cv_ingestion,
        "load_cv_file",
        lambda _path: (Path("candidate.docx"), b"Fallback CV text"),
    )

    def _raise_docx_error(_file_bytes: bytes) -> str:
        raise RuntimeError("docx parser unavailable")

    monkeypatch.setattr(cv_ingestion, "_extract_text_from_docx", _raise_docx_error)

    extracted = cv_ingestion.extract_cv_text("candidate.docx")
    assert extracted == "Fallback CV text"


def test_ingest_cv_cleans_and_segments(sample_txt_cv: Path) -> None:
    result = cv_ingestion.ingest_cv(sample_txt_cv)
    assert "\r" not in result.cleaned_text
    assert result.sections["summary"].startswith(
        "Senior engineer with distributed systems experience"
    )
    assert "Tech Lead - Example Corp" in result.sections["experience"]
    assert result.sections["skills"] == "Python, FastAPI, AWS"


def test_extract_cv_text_rejects_unsupported_format(tmp_path: Path) -> None:
    cv_path = tmp_path / "candidate.md"
    cv_path.write_text("# CV", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported CV format"):
        cv_ingestion.extract_cv_text(cv_path)
