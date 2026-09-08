"""Read-only helpers that prepare the latest processed run for the dashboard."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import median
from typing import Any

from src.settings import processed_data_root


SIGNAL_DISPLAY_NAMES = {
    "high_gdp_per_capita_change_low_life_expectancy_gain": "High GDP-per-capita change + low life-expectancy gain",
    "gdp_per_capita_increase_with_unemployment_increase": "GDP-per-capita increase + unemployment increase",
    "insufficient_core_data": "Some core data unavailable",
    "none": "None",
}

SUMMARY_SIGNAL_DISPLAY_NAMES = {
    "high_gdp_per_capita_change_low_life_expectancy_gain": "High GDP change + low life gain",
    "gdp_per_capita_increase_with_unemployment_increase": "GDP up + unemployment up",
    "insufficient_core_data": "Some core data unavailable",
    "none": "No research signal",
}


def core_data_status(row: dict[str, Any]) -> str:
    """Explain endpoint availability without making a missing value look like zero."""
    missing = [
        item.strip()
        for item in str(row.get("missing_core_metrics", "")).split(";")
        if item.strip()
    ]
    if not missing:
        return "All core data available"
    return f"Missing: {', '.join(missing)}"


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
    pointer_path = processed_data_root() / "latest_run.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
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
        "country_iso2_codes": country_iso2_codes(Path(pointer["raw_run_directory"]))
        if pointer.get("raw_run_directory")
        else {},
    }


def country_iso2_codes(raw_run_directory: Path) -> dict[str, str]:
    """Read ISO-2 codes from the saved World Bank country metadata for display only."""
    countries_directory = raw_run_directory / "countries"
    if not countries_directory.exists():
        return {}
    result: dict[str, str] = {}
    for page_path in countries_directory.glob("page_*.json"):
        payload = json.loads(page_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
            continue
        for record in payload[1]:
            iso3_code = record.get("id")
            iso2_code = record.get("iso2Code")
            if isinstance(iso3_code, str) and isinstance(iso2_code, str) and len(iso2_code) == 2:
                result[iso3_code] = iso2_code.upper()
    return result


def as_float(value: str | float | int | None) -> float | None:
    return None if value in {None, ""} else float(value)


def display_progress_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                "Research signals": ", ".join(
                    SIGNAL_DISPLAY_NAMES.get(signal, signal)
                    for signal in str(row["research_signals"]).split(";")
                ),
                "Why flagged": row.get("research_signal_explanation", ""),
                "Missing core metrics": row.get("missing_core_metrics", ""),
            }
        )
    return result


def display_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare a compact, first-screen country summary without hiding source metrics."""
    result: list[dict[str, Any]] = []
    for row in rows:
        signals = str(row["research_signals"]).split(";")
        descriptive_signals = [
            signal for signal in signals if signal not in {"none", "insufficient_core_data"}
        ]
        result.append(
            {
                "Country": row["country_name"],
                "World Bank region": row["region_name"].strip(),
                "GDP per capita change (%)": rounded_value(row["gdp_per_capita_change_pct"]),
                "Life expectancy change (years)": rounded_value(row["life_expectancy_change_years"]),
                "Research signal(s)": ", ".join(
                    SUMMARY_SIGNAL_DISPLAY_NAMES.get(signal, signal) for signal in descriptive_signals
                ) or "No descriptive signal",
                "Core-data status": core_data_status(row),
            }
        )
    return result


def display_all_comparison_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepare the full reference table, including supplementary context measures.

    Supplementary measures stay out of signal logic, but remain visible so an
    analyst can inspect the complete locally modelled country-period record.
    """
    result: list[dict[str, Any]] = []
    for row in rows:
        signals = str(row["research_signals"]).split(";")
        descriptive_signals = [
            signal for signal in signals if signal not in {"none", "insufficient_core_data"}
        ]
        result.append(
            {
                "Country": row["country_name"],
                "World Bank region": row["region_name"].strip(),
                "Income group": row["income_level_name"],
                "GDP per capita change (%)": rounded_value(row["gdp_per_capita_change_pct"]),
                "GDP growth change (pp)": rounded_value(row.get("gdp_per_capita_growth_change_pp")),
                "Life expectancy change (years)": rounded_value(row["life_expectancy_change_years"]),
                "Unemployment change (pp)": rounded_value(row["unemployment_change_pp"]),
                "Population change (%)": rounded_value(row["population_change_pct"]),
                "Secondary enrolment change (pp)": rounded_value(row.get("secondary_enrollment_change_pp")),
                "Research signal(s)": ", ".join(
                    SIGNAL_DISPLAY_NAMES.get(signal, signal) for signal in descriptive_signals
                ) or "No descriptive signal",
                "Core-data status": core_data_status(row),
            }
        )
    return result


def rounded_value(value: str | float | int | None) -> float | None:
    numeric_value = as_float(value)
    return None if numeric_value is None else round(numeric_value, 2)


def country_trend_rows(
    country_year_rows: list[dict[str, str]], country_code: str
) -> list[dict[str, Any]]:
    """Return a selected country's annual observations in chronological order."""
    measures = (
        "gdp_per_capita_constant_2015_usd",
        "gdp_per_capita_growth_annual_pct",
        "life_expectancy_years",
        "unemployment_total_pct",
        "population_total",
        "secondary_enrollment_gross_pct",
    )
    result = []
    for row in country_year_rows:
        if row["country_code"] != country_code:
            continue
        result.append(
            {
                "year": int(row["year"]),
                **{measure: as_float(row.get(measure)) for measure in measures},
            }
        )
    return sorted(result, key=lambda row: row["year"])


def peer_comparison(
    progress_rows: list[dict[str, Any]], selected_country_code: str, grouping: str
) -> dict[str, Any]:
    """Compare a selected country with median changes in its chosen peer group."""
    grouping_columns = {
        "Income group": ("income_level_id", "income_level_name"),
        "Region": ("region_id", "region_name"),
    }
    if grouping not in grouping_columns:
        raise DashboardDataError(f"Unsupported peer grouping: {grouping}")
    selected = next(
        (row for row in progress_rows if row["country_code"] == selected_country_code),
        None,
    )
    if selected is None:
        raise DashboardDataError(f"Selected country is not in the comparison: {selected_country_code}")
    group_id_column, group_name_column = grouping_columns[grouping]
    peers = [
        row
        for row in progress_rows
        if row["country_code"] != selected_country_code
        and row[group_id_column] == selected[group_id_column]
    ]
    metric_labels = {
        "gdp_per_capita_change_pct": "GDP per capita change (%)",
        "life_expectancy_change_years": "Life expectancy change (years)",
        "unemployment_change_pp": "Unemployment change (pp)",
        "population_change_pct": "Population change (%)",
    }
    metrics = []
    for field, label in metric_labels.items():
        peer_values = [as_float(row.get(field)) for row in peers]
        peer_values = [value for value in peer_values if value is not None]
        selected_value = as_float(selected.get(field))
        peer_median = median(peer_values) if peer_values else None
        metrics.append(
            {
                "Metric": label,
                "Selected country": rounded_value(selected_value),
                "Peer median": rounded_value(peer_median),
                "Difference from peer median": (
                    rounded_value(selected_value - peer_median)
                    if selected_value is not None and peer_median is not None
                    else None
                ),
                "Peer observations": len(peer_values),
            }
        )
    return {
        "grouping": grouping,
        "group_name": selected[group_name_column].strip(),
        "peer_count": len(peers),
        "member_names": sorted(
            str(row.get("country_name") or row["country_code"]) for row in peers
        ),
        "members": sorted(
            (
                {
                    "country_code": str(row["country_code"]),
                    "country_name": str(row.get("country_name") or row["country_code"]),
                }
                for row in peers
            ),
            key=lambda row: row["country_name"],
        ),
        "metrics": metrics,
    }
