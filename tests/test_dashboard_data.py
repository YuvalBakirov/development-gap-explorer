import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.dashboard_data import (
    core_data_status,
    country_trend_rows,
    display_all_comparison_rows,
    display_progress_rows,
    display_summary_rows,
    load_dashboard_data,
    peer_comparison,
)


class DashboardDataTests(unittest.TestCase):
    def test_core_data_status_is_explicit_about_completeness_and_missing_values(self):
        self.assertEqual(core_data_status({"missing_core_metrics": ""}), "All core data available")
        self.assertEqual(
            core_data_status({"missing_core_metrics": "GDP per capita;Unemployment"}),
            "Missing: GDP per capita, Unemployment",
        )

    def test_summary_keeps_data_quality_separate_from_research_signals(self):
        row = {
            "country_name": "Exampleland",
            "region_name": "Example region",
            "gdp_per_capita_change_pct": "",
            "life_expectancy_change_years": "1.0",
            "research_signals": "insufficient_core_data",
            "missing_core_metrics": "GDP per capita",
        }
        result = display_summary_rows([row])[0]
        self.assertEqual(result["Research signal(s)"], "No descriptive signal")
        self.assertEqual(result["Core-data status"], "Missing: GDP per capita")

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

    def test_display_summary_rows_keeps_first_screen_compact(self):
        result = display_summary_rows(
            [{
                "country_name": "Example",
                "region_name": " Region ",
                "gdp_per_capita_change_pct": "12.5",
                "life_expectancy_change_years": "1.2",
                "research_signals": "gdp_per_capita_increase_with_unemployment_increase",
                "missing_core_metrics": "",
            }]
        )
        self.assertEqual(
            list(result[0]),
            [
                "Country",
                "World Bank region",
                "GDP per capita change (%)",
                "Life expectancy change (years)",
                "Research signal(s)",
                "Core-data status",
            ],
        )
        self.assertEqual(result[0]["Research signal(s)"], "GDP up + unemployment up")
        self.assertEqual(result[0]["Core-data status"], "All core data available")

    def test_all_comparisons_include_core_and_supplementary_changes(self):
        result = display_all_comparison_rows(
            [{
                "country_name": "Example",
                "region_name": " Region ",
                "income_level_name": "High income",
                "gdp_per_capita_change_pct": "12.5",
                "gdp_per_capita_growth_change_pp": "-1.25",
                "life_expectancy_change_years": "1.2",
                "unemployment_change_pp": "",
                "population_change_pct": "3.0",
                "secondary_enrollment_change_pp": "2.5",
                "research_signals": "none",
                "missing_core_metrics": "Unemployment",
            }]
        )[0]
        self.assertEqual(result["GDP growth change (pp)"], -1.25)
        self.assertEqual(result["Secondary enrolment change (pp)"], 2.5)
        self.assertIsNone(result["Unemployment change (pp)"])
        self.assertEqual(result["Research signal(s)"], "No descriptive signal")

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

    def test_peer_comparison_uses_median_and_excludes_selected_country(self):
        rows = [
            {"country_code": "AAA", "country_name": "Alpha", "income_level_id": "HIC", "income_level_name": "High income", "region_id": "R", "region_name": "Region", "gdp_per_capita_change_pct": 20, "life_expectancy_change_years": 2, "unemployment_change_pp": 1, "population_change_pct": 5},
            {"country_code": "BBB", "country_name": "Beta", "income_level_id": "HIC", "income_level_name": "High income", "region_id": "R", "region_name": "Region", "gdp_per_capita_change_pct": 10, "life_expectancy_change_years": 1, "unemployment_change_pp": 0, "population_change_pct": 4},
            {"country_code": "CCC", "country_name": "Gamma", "income_level_id": "HIC", "income_level_name": "High income", "region_id": "R", "region_name": "Region", "gdp_per_capita_change_pct": 30, "life_expectancy_change_years": 3, "unemployment_change_pp": 2, "population_change_pct": 6},
        ]
        result = peer_comparison(rows, "AAA", "Income group")
        self.assertEqual(result["peer_count"], 2)
        self.assertEqual(result["metrics"][0]["Peer median"], 20.0)
        self.assertEqual(result["metrics"][0]["Difference from peer median"], 0.0)
        self.assertEqual(result["member_names"], ["Beta", "Gamma"])
        self.assertEqual(
            result["members"],
            [
                {"country_code": "BBB", "country_name": "Beta"},
                {"country_code": "CCC", "country_name": "Gamma"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
