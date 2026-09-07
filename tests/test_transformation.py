import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.settings import INDICATORS
from src.transformation import transform_raw_run


def write_page(directory: Path, rows: list[dict[str, object]]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "page_001.json").write_text(
        json.dumps([{"page": "1", "pages": "1", "total": str(len(rows))}, rows]),
        encoding="utf-8",
    )


class TransformationTests(unittest.TestCase):
    def test_transform_builds_country_year_table_and_skips_aggregates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_run = root / "raw" / "run-test"
            write_page(
                raw_run / "countries",
                [
                    {
                        "id": "USA",
                        "name": "United States",
                        "region": {"id": "NAC", "value": "North America"},
                        "incomeLevel": {"id": "HIC", "value": "High income"},
                    },
                    {
                        "id": "WLD",
                        "name": "World",
                        "region": {"id": "NA", "value": "Aggregates"},
                        "incomeLevel": {"id": "NA", "value": "Aggregates"},
                    },
                ],
            )
            (raw_run / "manifest.json").write_text(json.dumps({"run_id": "run-test"}), encoding="utf-8")
            values = {
                "NY.GDP.PCAP.KD": 50000,
                "NY.GDP.PCAP.KD.ZG": 2.0,
                "SL.UEM.TOTL.ZS": 5.0,
                "SP.DYN.LE00.IN": 79.0,
                "SP.POP.TOTL": 300000000,
                "SE.SEC.ENRR": 95.0,
            }
            for indicator in INDICATORS:
                write_page(
                    raw_run / "indicators" / indicator.code,
                    [
                        {
                            "indicator": {"id": indicator.code},
                            "countryiso3code": "USA",
                            "date": "2010",
                            "value": values[indicator.code],
                        },
                        {
                            "indicator": {"id": indicator.code},
                            "countryiso3code": "WLD",
                            "date": "2010",
                            "value": values[indicator.code],
                        },
                    ],
                )

            summary = transform_raw_run(raw_run, root / "processed")
            self.assertEqual(summary["country_year_rows"], 15)
            processed_run = root / "processed" / "run-test"
            with (processed_run / "country_year.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["country_code"], "USA")
            self.assertEqual(rows[0]["gdp_per_capita_constant_2015_usd"], "50000")
            quality = json.loads((processed_run / "data_quality_report.json").read_text())
            self.assertEqual(quality["aggregate_observations_skipped"], len(INDICATORS))
            self.assertEqual(quality["status"], "passed_with_missing_values")


if __name__ == "__main__":
    unittest.main()
