import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.dashboard_data import country_trend_rows, display_progress_rows, load_dashboard_data


class DashboardDataTests(unittest.TestCase):
    def test_display_progress_rows_converts_numbers_and_labels(self):
        result = display_progress_rows(
            [{
                "country_name": "Example",
                "region_name": " Region ",
                "income_level_name": "Low income",
                "gdp_per_capita_change_pct": "12.5",
                "life_expectancy_change_years": "1.2",
                "unemployment_change_pp": "",
                "population_change_pct": "3.0",
                "research_signals": "none",
            }]
        )
        self.assertEqual(result[0]["Region"], "Region")
        self.assertEqual(result[0]["GDP per capita change (%)"], 12.5)
        self.assertIsNone(result[0]["Unemployment change (pp)"])
        self.assertEqual(result[0]["Research signals"], "None")

    def test_country_trend_rows_are_sorted_and_numeric(self):
        rows = [
            {"country_code": "AAA", "year": "2011", "gdp_per_capita_constant_2015_usd": "11", "life_expectancy_years": "61", "unemployment_total_pct": "", "population_total": "101"},
            {"country_code": "AAA", "year": "2010", "gdp_per_capita_constant_2015_usd": "10", "life_expectancy_years": "60", "unemployment_total_pct": "5", "population_total": "100"},
            {"country_code": "BBB", "year": "2010", "gdp_per_capita_constant_2015_usd": "1", "life_expectancy_years": "1", "unemployment_total_pct": "1", "population_total": "1"},
        ]
        trend = country_trend_rows(rows, "AAA")
        self.assertEqual([row["year"] for row in trend], [2010, 2011])
        self.assertIsNone(trend[1]["unemployment_total_pct"])

    def test_load_dashboard_data_uses_latest_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run = root / "run-1"
            run.mkdir()
            (root / "latest_run.json").write_text(json.dumps({"processed_run_directory": str(run)}), encoding="utf-8")
            for name, headers in {
                "country_progress_2010_2024.csv": ["country_code"],
                "country_year.csv": ["country_code"],
            }.items():
                with (run / name).open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=headers)
                    writer.writeheader()
            (run / "metrics_summary_2010_2024.json").write_text("{}", encoding="utf-8")
            (run / "metric_definitions_2010_2024.json").write_text("{}", encoding="utf-8")
            (run / "data_quality_report.json").write_text("{}", encoding="utf-8")
            with patch("src.dashboard_data.processed_data_root", return_value=root):
                loaded = load_dashboard_data()
            self.assertEqual(loaded["run_directory"], run)


if __name__ == "__main__":
    unittest.main()
