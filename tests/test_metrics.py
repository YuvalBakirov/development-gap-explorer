import csv
import tempfile
import unittest
from pathlib import Path

from src.metrics import MetricsError, build_country_progress, percentage_change


FIELDS = [
    "country_code", "country_name", "region_id", "region_name", "income_level_id",
    "income_level_name", "year", "gdp_per_capita_constant_2015_usd",
    "life_expectancy_years", "unemployment_total_pct", "population_total",
]


def row(code: str, year: int, gdp: object, life: object, unemployment: object, population: object) -> dict[str, object]:
    return {
        "country_code": code, "country_name": code, "region_id": "R", "region_name": "Region",
        "income_level_id": "HIC", "income_level_name": "High income", "year": year,
        "gdp_per_capita_constant_2015_usd": gdp, "life_expectancy_years": life,
        "unemployment_total_pct": unemployment, "population_total": population,
    }


class MetricsTests(unittest.TestCase):
    def test_percentage_change_requires_nonzero_start(self) -> None:
        self.assertEqual(percentage_change(100, 125), 25.0)
        self.assertIsNone(percentage_change(0, 125))

    def test_metrics_calculate_signals_without_imputing_missing_data(self) -> None:
        rows = [
            row("AAA", 2010, 100, 70, 5, 1000), row("AAA", 2024, 200, 70.1, 6, 1100),
            row("BBB", 2010, 100, 70, 5, 1000), row("BBB", 2024, 110, 71, 4, 1100),
            row("CCC", 2010, 100, 70, 5, 1000), row("CCC", 2024, 120, 72, 3, 1100),
            row("DDD", 2010, 100, 70, "", 1000), row("DDD", 2024, 130, 73, "", 1100),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "country_year.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            summary = build_country_progress(source, root / "metrics", 2010, 2024)
            self.assertEqual(summary["country_count"], 4)
            self.assertEqual(summary["countries_with_complete_core_metrics"], 3)
            with (root / "metrics" / "country_progress_2010_2024.csv").open(encoding="utf-8", newline="") as handle:
                result = {item["country_code"]: item for item in csv.DictReader(handle)}
            self.assertIn("high_gdp_growth_low_life_expectancy_gain", result["AAA"]["research_signals"])
            self.assertIn("gdp_growth_with_unemployment_increase", result["AAA"]["research_signals"])
            self.assertEqual(result["DDD"]["unemployment_change_pp"], "")
            self.assertIn("insufficient_core_data", result["DDD"]["research_signals"])

    def test_metrics_reject_reverse_period(self) -> None:
        with self.assertRaises(MetricsError):
            build_country_progress(Path("missing.csv"), Path("output"), 2024, 2010)


if __name__ == "__main__":
    unittest.main()
