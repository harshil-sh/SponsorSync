"""Utilities for syncing licensed sponsors from a CSV feed into SQLite."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen


COMPANY_COLUMN_CANDIDATES = ("company", "company_name", "sponsor", "sponsor_name")


@dataclass(frozen=True)
class SponsorRecord:
    company_name: str
    normalized_company_name: str
    row_data: dict[str, str]


def remove_unprintable(text: str) -> str:
    """Remove non-printable characters without aggressive normalization."""
    return "".join(ch for ch in text if ch.isprintable())


def normalize_company_name(company_name: str) -> str:
    """Normalize only by removing unprintable characters and trimming edges."""
    return remove_unprintable(company_name).strip()


def _detect_company_column(field_names: Iterable[str] | None) -> str:
    if not field_names:
        raise ValueError("CSV header is missing.")

    for name in field_names:
        lowered = name.strip().lower()
        if lowered in COMPANY_COLUMN_CANDIDATES:
            return name

    raise ValueError(
        "CSV is missing a company column. Expected one of: "
        + ", ".join(COMPANY_COLUMN_CANDIDATES)
    )


def fetch_latest_licensed_sponsors(csv_url: str) -> list[SponsorRecord]:
    """Fetch a licensed sponsors CSV and return parsed sponsor records."""
    with urlopen(csv_url) as response:
        csv_bytes = response.read()

    csv_text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(csv_text))
    company_column = _detect_company_column(reader.fieldnames)

    records: list[SponsorRecord] = []
    for row in reader:
        raw_company_name = row.get(company_column, "")
        company_name = raw_company_name if raw_company_name is not None else ""
        records.append(
            SponsorRecord(
                company_name=company_name,
                normalized_company_name=normalize_company_name(company_name),
                row_data=row,
            )
        )

    return records


def store_sponsors_in_sqlite(records: Iterable[SponsorRecord], db_path: str | Path) -> int:
    """Store records in SQLite, preserving duplicates."""
    connection = sqlite3.connect(str(db_path))
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS licensed_sponsors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                normalized_company_name TEXT NOT NULL,
                row_data TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )

        fetched_at = datetime.now(timezone.utc).isoformat()
        inserted = 0
        for record in records:
            connection.execute(
                """
                INSERT INTO licensed_sponsors (
                    company_name,
                    normalized_company_name,
                    row_data,
                    fetched_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    record.company_name,
                    record.normalized_company_name,
                    json.dumps(record.row_data, ensure_ascii=False),
                    fetched_at,
                ),
            )
            inserted += 1

        connection.commit()
        return inserted
    finally:
        connection.close()


def sync_licensed_sponsors(csv_url: str, db_path: str | Path) -> int:
    """Fetch latest CSV and store rows in SQLite."""
    records = fetch_latest_licensed_sponsors(csv_url)
    return store_sponsors_in_sqlite(records, db_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch latest licensed sponsors CSV and store it in SQLite."
    )
    parser.add_argument("csv_url", help="URL to the licensed sponsors CSV file")
    parser.add_argument(
        "--db-path",
        default="licensed_sponsors.db",
        help="Path to SQLite database file (default: licensed_sponsors.db)",
    )

    args = parser.parse_args()
    inserted = sync_licensed_sponsors(args.csv_url, args.db_path)
    print(f"Inserted {inserted} rows into {args.db_path}")


if __name__ == "__main__":
    main()
