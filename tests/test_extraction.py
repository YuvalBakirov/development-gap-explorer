import json
import tempfile
import unittest
from pathlib import Path

from src.extraction import fetch_resource_to_directory, is_country_or_economy


class FakeClient:
    def get_page(self, _resource: str, _params: dict[str, str], page: int) -> list[object]:
        rows = [{"id": "row-1-a"}] if page == 1 else [{"id": "row-2-a"}, {"id": "row-2-b"}]
        return [{"page": str(page), "pages": "2", "total": "3"}, rows]


class ExtractionTests(unittest.TestCase):
    def test_country_metadata_rule_includes_country(self) -> None:
        self.assertTrue(
            is_country_or_economy(
                {"id": "USA", "region": {"id": "NAC", "value": "North America"}}
            )
        )

    def test_country_metadata_rule_excludes_aggregate(self) -> None:
        self.assertFalse(
            is_country_or_economy(
                {"id": "WLD", "region": {"id": "NA", "value": "Aggregates"}}
            )
        )

    def test_fetch_resource_writes_all_pages_and_validates_total(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            summary = fetch_resource_to_directory(
                FakeClient(), "country", {"format": "json"}, Path(directory)
            )
            self.assertEqual(summary["page_row_counts"], [1, 2])
            self.assertEqual(summary["total_rows"], 3)
            self.assertTrue((Path(directory) / "page_001.json").exists())
            second_page = json.loads((Path(directory) / "page_002.json").read_text())
            self.assertEqual(len(second_page[1]), 2)


if __name__ == "__main__":
    unittest.main()
