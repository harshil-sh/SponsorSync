"""CV ingestion utilities for loading, extracting, and segmenting candidate CV text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CVIngestionResult:
    """Normalized CV text plus lightweight section segmentation."""

    raw_text: str
    cleaned_text: str
    sections: dict[str, str]


def load_cv_file(cv_path: str | Path) -> tuple[Path, bytes]:
    """Load CV file from disk and return canonical path + bytes."""

    path = Path(cv_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"CV file not found: {path}")

    return path, path.read_bytes()


def _extract_text_from_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8")


def _extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dependency may be optional
        raise RuntimeError(
            "DOCX extraction requires python-docx. Install it to parse .docx CV files."
        ) from exc

    from io import BytesIO

    document = Document(BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dependency may be optional
        raise RuntimeError(
            "PDF extraction requires pypdf. Install it to parse .pdf CV files."
        ) from exc

    from io import BytesIO

    reader = PdfReader(BytesIO(file_bytes))
    extracted_chunks: list[str] = []
    for page in reader.pages:
        extracted_chunks.append(page.extract_text() or "")
    return "\n".join(extracted_chunks)


def extract_cv_text(cv_path: str | Path) -> str:
    """Extract text from supported CV file types with deterministic fallback."""

    path, file_bytes = load_cv_file(cv_path)
    suffix = path.suffix.lower()

    adapters: dict[str, tuple] = {
        ".txt": (_extract_text_from_txt,),
        ".docx": (_extract_text_from_docx, _extract_text_from_txt),
        ".pdf": (_extract_text_from_pdf, _extract_text_from_txt),
    }
    if suffix not in adapters:
        raise ValueError(f"Unsupported CV format: {suffix or '<none>'}")

    last_error: Exception | None = None
    for adapter in adapters[suffix]:
        try:
            text = adapter(file_bytes)
            if text.strip():
                return text
        except (
            Exception
        ) as exc:  # pragma: no cover - exact errors depend on parser libs
            last_error = exc

    if last_error is not None:
        raise RuntimeError(
            f"Failed to extract CV text from {path.name}"
        ) from last_error

    raise RuntimeError(f"Failed to extract CV text from {path.name}: no readable text")


def clean_cv_text(raw_text: str) -> str:
    """Normalize whitespace and common artifacts while preserving line boundaries."""

    normalized_newlines = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    without_nulls = normalized_newlines.replace("\x00", "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in without_nulls.split("\n")]

    collapsed_blank_lines: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line
        if is_blank and previous_blank:
            continue
        collapsed_blank_lines.append(line)
        previous_blank = is_blank

    return "\n".join(collapsed_blank_lines).strip()


def segment_cv_sections(cleaned_text: str) -> dict[str, str]:
    """Create basic CV sections based on common heading labels."""

    heading_map = {
        "summary": "summary",
        "professional summary": "summary",
        "experience": "experience",
        "work experience": "experience",
        "employment": "experience",
        "skills": "skills",
        "technical skills": "skills",
        "education": "education",
        "certifications": "certifications",
        "projects": "projects",
    }

    sections: dict[str, list[str]] = {}
    current_section = "general"
    sections[current_section] = []

    for line in cleaned_text.split("\n"):
        key = line.strip().lower().rstrip(":")
        mapped = heading_map.get(key)
        if mapped is not None:
            current_section = mapped
            sections.setdefault(current_section, [])
            continue

        sections.setdefault(current_section, []).append(line)

    return {
        section: "\n".join(content).strip()
        for section, content in sections.items()
        if any(chunk.strip() for chunk in content)
    }


def ingest_cv(cv_path: str | Path) -> CVIngestionResult:
    """Run end-to-end CV ingestion for extraction, cleaning, and sectioning."""

    raw_text = extract_cv_text(cv_path)
    cleaned_text = clean_cv_text(raw_text)
    sections = segment_cv_sections(cleaned_text)
    return CVIngestionResult(
        raw_text=raw_text, cleaned_text=cleaned_text, sections=sections
    )
