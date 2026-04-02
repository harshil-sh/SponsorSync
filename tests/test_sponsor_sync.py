import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sponsor_sync import normalize_company_name, sync_licensed_sponsors


class SponsorSyncTests(unittest.TestCase):
    def test_sync_loads_csv_data_into_sqlite_and_keeps_duplicates(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_path = temp_path / "licensed_sponsors.csv"
            db_path = temp_path / "sponsors.db"

            csv_path.write_text(
                "company,license_id\n"
                "Acme Corp,1001\n"
                "Acme Corp,1002\n"
                "Byte\x0bWorks,1003\n",
                encoding="utf-8",
            )

            inserted = sync_licensed_sponsors(csv_path.as_uri(), db_path)
            self.assertEqual(inserted, 3)

            connection = sqlite3.connect(db_path)
            try:
                count = connection.execute(
                    "SELECT COUNT(*) FROM licensed_sponsors"
                ).fetchone()[0]
                self.assertGreater(count, 0)

                duplicate_count = connection.execute(
                    "SELECT COUNT(*) FROM licensed_sponsors WHERE company_name = ?",
                    ("Acme Corp",),
                ).fetchone()[0]
                self.assertEqual(duplicate_count, 2)

                normalized = connection.execute(
                    "SELECT normalized_company_name FROM licensed_sponsors "
                    "WHERE company_name = ?",
                    ("Byte\x0bWorks",),
                ).fetchone()[0]
                self.assertEqual(normalized, "ByteWorks")
            finally:
                connection.close()

    def test_normalization_removes_only_unprintable_characters(self) -> None:
        self.assertEqual(normalize_company_name("  A\x00CME LLC  "), "ACME LLC")


if __name__ == "__main__":
    unittest.main()
