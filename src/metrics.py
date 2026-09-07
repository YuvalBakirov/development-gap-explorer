"""Business-facing, descriptive metrics for the Development Gap Explorer."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from src.extraction import write_json_atomic
from src.transformation import write_csv_atomic


class MetricsError(ValueError):
    """Raised when the processed country-year table cannot support metrics."""


MEASURE_COLUMNS = (
    "gdp_per_capita_constant_2015_usd",
    "life_expectancy_years",
    "unemployment_total_pct",
    "population_total",
)


def nullable_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise MetricsError(f"Expected numeric value, received {value!r}") from exc


def percentage_change(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start == 0:
        return None
    return round((end - start) / start * 100, 4)


def difference(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return round(end - start, 4)


def nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise MetricsError("Cannot calculate a percentile from no values")
    if not 0 < percentile <= 1:
        raise MetricsError("Percentile must be in the interval (0, 1]")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def load_period_endpoints(
    country_year_path: Path, start_year: int, end_year: int
) -> dict[str, dict[str, dict[str, Any]]]:
    if start_year >= end_year:
        raise MetricsError("Start year must be earlier than end year")
    endpoints: dict[str, dict[str, dict[str, Any]]] = {}
    with country_year_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"country_code", "year", *MEASURE_COLUMNS}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise MetricsError("Country-year table is missing required metric columns")
        for row in reader:
            year = int(row["year"])
            if year not in {start_year, end_year}:
                continue
            country_endpoints = endpoints.setdefault(row["country_code"], {})
            label = "start" if year == start_year else "end"
            if label in country_endpoints:
                raise MetricsError(f"Duplicate country-year row for {row['country_code']} in {year}")
            country_endpoints[label] = row
    return endpoints


def build_country_progress(
    country_year_path: Path, output_directory: Path, start_year: int, end_year: int
) -> dict[str, Any]:
    """Calculate period changes and transparent signals for research prioritization."""
    endpoints = load_period_endpoints(country_year_path, start_year, end_year)
    progress_rows: list[dict[str, Any]] = []
    for country_code, period in sorted(endpoints.items()):
        start, end = period.get("start"), period.get("end")
        metadata = start or end
        if metadata is None:
            continue
        start_values = {column: nullable_float(start.get(column)) if start else None for column in MEASURE_COLUMNS}
        end_values = {column: nullable_float(end.get(column)) if end else None for column in MEASURE_COLUMNS}
        row = {
            "country_code": country_code,
            "country_name": metadata["country_name"],
            "region_id": metadata["region_id"],
            "region_name": metadata["region_name"],
            "income_level_id": metadata["income_level_id"],
            "income_level_name": metadata["income_level_name"],
            "start_year": start_year,
            "end_year": end_year,
            "gdp_per_capita_start": start_values["gdp_per_capita_constant_2015_usd"],
            "gdp_per_capita_end": end_values["gdp_per_capita_constant_2015_usd"],
            "gdp_per_capita_change_pct": percentage_change(start_values["gdp_per_capita_constant_2015_usd"], end_values["gdp_per_capita_constant_2015_usd"]),
            "life_expectancy_start": start_values["life_expectancy_years"],
            "life_expectancy_end": end_values["life_expectancy_years"],
            "life_expectancy_change_years": difference(start_values["life_expectancy_years"], end_values["life_expectancy_years"]),
            "unemployment_start_pct": start_values["unemployment_total_pct"],
            "unemployment_end_pct": end_values["unemployment_total_pct"],
            "unemployment_change_pp": difference(start_values["unemployment_total_pct"], end_values["unemployment_total_pct"]),
            "population_start": start_values["population_total"],
            "population_end": end_values["population_total"],
            "population_change_pct": percentage_change(start_values["population_total"], end_values["population_total"]),
        }
        row["core_metrics_available"] = all(
            row[field] is not None
            for field in ("gdp_per_capita_change_pct", "life_expectancy_change_years", "unemployment_change_pp", "population_change_pct")
        )
        progress_rows.append(row)

    gdp_changes = [row["gdp_per_capita_change_pct"] for row in progress_rows if row["gdp_per_capita_change_pct"] is not None]
    life_changes = [row["life_expectancy_change_years"] for row in progress_rows if row["life_expectancy_change_years"] is not None]
    high_gdp_threshold = nearest_rank(gdp_changes, 0.75)
    low_life_threshold = nearest_rank(life_changes, 0.25)
    for row in progress_rows:
        signals: list[str] = []
        if row["gdp_per_capita_change_pct"] is not None and row["life_expectancy_change_years"] is not None:
            if row["gdp_per_capita_change_pct"] >= high_gdp_threshold and row["life_expectancy_change_years"] <= low_life_threshold:
                signals.append("high_gdp_growth_low_life_expectancy_gain")
        if row["gdp_per_capita_change_pct"] is not None and row["unemployment_change_pp"] is not None:
            if row["gdp_per_capita_change_pct"] > 0 and row["unemployment_change_pp"] > 0:
                signals.append("gdp_growth_with_unemployment_increase")
        if not row["core_metrics_available"]:
            signals.append("insufficient_core_data")
        row["research_signals"] = ";".join(signals) if signals else "none"

    if not progress_rows:
        raise MetricsError("No countries found in the requested period")
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / f"country_progress_{start_year}_{end_year}.csv"
    write_csv_atomic(output_path, progress_rows, list(progress_rows[0]))
    definitions = {
        "period": {"start_year": start_year, "end_year": end_year},
        "gdp_per_capita_change_pct": "Percent change in GDP per capita at constant 2015 US dollars.",
        "life_expectancy_change_years": "End-year life expectancy minus start-year life expectancy, in years.",
        "unemployment_change_pp": "End-year unemployment rate minus start-year unemployment rate, in percentage points.",
        "population_change_pct": "Percent change in total population.",
        "high_gdp_growth_low_life_expectancy_gain": {"gdp_threshold": high_gdp_threshold, "life_expectancy_threshold": low_life_threshold},
        "limitation": "Signals prioritize research questions; they do not establish causality, forecast outcomes, rate countries, or provide investment advice.",
    }
    summary = {
        "period": {"start_year": start_year, "end_year": end_year},
        "country_count": len(progress_rows),
        "countries_with_complete_core_metrics": sum(1 for row in progress_rows if row["core_metrics_available"]),
        "signal_counts": {signal: sum(signal in row["research_signals"].split(";") for row in progress_rows) for signal in ("high_gdp_growth_low_life_expectancy_gain", "gdp_growth_with_unemployment_increase", "insufficient_core_data")},
        "output_file": str(output_path),
    }
    write_json_atomic(output_directory / f"metric_definitions_{start_year}_{end_year}.json", definitions)
    write_json_atomic(output_directory / f"metrics_summary_{start_year}_{end_year}.json", summary)
    return summary

