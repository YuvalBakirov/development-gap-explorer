"""Read-only helpers that prepare the latest processed run for the dashboard."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.settings import processed_data_root


SIGNAL_DISPLAY_NAMES = {
    "high_gdp_growth_low_life_expectancy_gain": "GDP growth + low life-expectancy gain",
    "gdp_growth_with_unemployment_increase": "GDP growth + unemployment increase",
    "insufficient_core_data": "Missing core data",
    "none": "None",
}


class DashboardDataError(ValueError):
    """Raised when a successful ETL output is unavailable or malformed."""


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise DashboardDataError(f"Required dashboard file was not found: {path.name}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def latest_run_directory() -> Path:
    pointer_path = processed_data_root() / "latest_run.json"
    if not pointer_path.exists():
        raise DashboardDataError("No successful ETL run found. Run `python etl.py` first.")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    run_directory = Path(pointer["processed_run_directory"])
    if not run_directory.exists():
        raise DashboardDataError("The latest ETL run directory is unavailable.")
    return run_directory


def load_dashboard_data() -> dict[str, Any]:
    """Load the latest output without changing data or calling the API."""
    run_directory = latest_run_directory()
    progress_files = sorted(run_directory.glob("country_progress_*.csv"))
    summary_files = sorted(run_directory.glob("metrics_summary_*.json"))
    if len(progress_files) != 1 or len(summary_files) != 1:
        raise DashboardDataError("Latest ETL run is missing its country progress metrics.")

    return {
        "run_directory": run_directory,
        "progress_rows": read_csv_rows(progress_files[0]),
        "country_year_rows": read_csv_rows(run_directory / "country_year.csv"),
        "quality": json.loads((run_directory / "data_quality_report.json").read_text(encoding="utf-8")),
        "metrics_summary": json.loads(summary_files[0].read_text(encoding="utf-8")),
        "metric_definitions": json.loads(
            next(run_directory.glob("metric_definitions_*.json")).read_text(encoding="utf-8")
        ),
    }


def as_float(value: str | None) -> float | None:
    return None if value in {None, ""} else float(value)


def display_progress_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Convert compact processed fields into labels and numbers for display."""
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "Country": row["country_name"],
                "Region": row["region_name"].strip(),
                "Income group": row["income_level_name"],
                "GDP per capita change (%)": rounded_value(row["gdp_per_capita_change_pct"]),
                "Life expectancy change (years)": rounded_value(row["life_expectancy_change_years"]),
                "Unemployment change (pp)": rounded_value(row["unemployment_change_pp"]),
                "Population change (%)": rounded_value(row["population_change_pct"]),
                "Research signals": "; ".join(
                    SIGNAL_DISPLAY_NAMES.get(signal, signal)
                    for signal in row["research_signals"].split(";")
                ),
            }
        )
    return result


def rounded_value(value: str | None) -> float | None:
    numeric_value = as_float(value)
    return None if numeric_value is None else round(numeric_value, 2)


def country_trend_rows(
    country_year_rows: list[dict[str, str]], country_code: str
) -> list[dict[str, Any]]:
    """Return a selected country's annual observations in chronological order."""
    measures = (
        "gdp_per_capita_constant_2015_usd",
        "life_expectancy_years",
        "unemployment_total_pct",
        "population_total",
    )
    result = []
    for row in country_year_rows:
        if row["country_code"] != country_code:
            continue
        result.append({"year": int(row["year"]), **{measure: as_float(row[measure]) for measure in measures}})
    return sorted(result, key=lambda row: row["year"])
