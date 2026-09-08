import csv
import tempfile
import unittest
from pathlib import Path

from src.metrics import (
    GDP_PER_CAPITA_INCREASE_WITH_UNEMPLOYMENT_INCREASE,
    HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN,
    MetricsError,
    build_country_progress,
    calculate_country_progress,
    percentage_change,
)


FIELDS = [
    "country_code", "country_name", "region_id", "region_name", "income_level_id",
    "income_level_name", "year", "gdp_per_capita_constant_2015_usd",
    "gdp_per_capita_growth_annual_pct", "life_expectancy_years", "unemployment_total_pct",
    "population_total", "secondary_enrollment_gross_pct",
]


def row(code: str, year: int, gdp: object, life: object, unemployment: object, population: object, growth: object = 2, enrolment: object = 80) -> dict[str, object]:
    return {
        "country_code": code, "country_name": code, "region_id": "R", "region_name": "Region",
        "income_level_id": "HIC", "income_level_name": "High income", "year": year,
        "gdp_per_capita_constant_2015_usd": gdp, "life_expectancy_years": life,
        "gdp_per_capita_growth_annual_pct": growth, "unemployment_total_pct": unemployment,
        "population_total": population, "secondary_enrollment_gross_pct": enrolment,
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
            self.assertIn(HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN, result["AAA"]["research_signals"])
            self.assertIn(GDP_PER_CAPITA_INCREASE_WITH_UNEMPLOYMENT_INCREASE, result["AAA"]["research_signals"])
            self.assertEqual(result["DDD"]["unemployment_change_pp"], "")
            self.assertEqual(result["AAA"]["gdp_per_capita_growth_change_pp"], "0.0")
            self.assertEqual(result["AAA"]["secondary_enrollment_change_pp"], "0.0")
            self.assertIn("insufficient_core_data", result["DDD"]["research_signals"])
            self.assertIn("Missing core metrics", result["DDD"]["research_signal_explanation"])

    def test_metrics_can_recalculate_a_different_period_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "country_year.csv"
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows([
                    row("AAA", 2015, 100, 70, 5, 1000),
                    row("AAA", 2020, 125, 72, 4, 1100),
                    row("BBB", 2015, 100, 70, 5, 1000),
                    row("BBB", 2020, 110, 71, 5, 1100),
                ])
            progress_rows, definitions, summary = calculate_country_progress(source, 2015, 2020)
            self.assertEqual(summary["period"], {"start_year": 2015, "end_year": 2020})
            self.assertEqual(len(progress_rows), 2)
            self.assertIn(HIGH_GDP_PER_CAPITA_CHANGE_LOW_LIFE_EXPECTANCY_GAIN, definitions)
            self.assertFalse((root / "country_progress_2015_2020.csv").exists())

    def test_metrics_reject_reverse_period(self) -> None:
        with self.assertRaises(MetricsError):
            build_country_progress(Path("missing.csv"), Path("output"), 2024, 2010)


if __name__ == "__main__":
    unittest.main()
