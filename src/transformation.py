"""Transform saved World Bank API pages into an analytical country-year table."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from src.extraction import is_country_or_economy, write_json_atomic
from src.settings import END_YEAR, INDICATORS, START_YEAR


def write_csv_atomic(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    temporary_path.replace(path)


def read_api_pages(directory: Path) -> Iterable[list[Any]]:
    page_paths = sorted(directory.glob("page_*.json"))
    if not page_paths:
        raise FileNotFoundError(f"No API pages found in {directory}")
    for page_path in page_paths:
        payload = json.loads(page_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or len(payload) != 2:
            raise ValueError(f"Invalid raw API page: {page_path}")
        if not isinstance(payload[0], dict) or not isinstance(payload[1], list):
            raise ValueError(f"Invalid raw API envelope: {page_path}")
        yield payload


def _country_dimension(record: dict[str, Any]) -> dict[str, Any]:
    region = record.get("region") or {}
    income_level = record.get("incomeLevel") or {}
    return {
        "country_code": record["id"],
        "country_name": record.get("name"),
        "region_id": region.get("id"),
        "region_name": region.get("value"),
        "income_level_id": income_level.get("id"),
        "income_level_name": income_level.get("value"),
    }


def _is_valid_value(indicator_code: str, value: float | int) -> bool:
    if indicator_code in {"NY.GDP.PCAP.KD", "SP.POP.TOTL", "SE.SEC.ENRR"}:
        return value >= 0
    if indicator_code == "SL.UEM.TOTL.ZS":
        return 0 <= value <= 100
    if indicator_code == "SP.DYN.LE00.IN":
        return 0 < value <= 120
    return True


def transform_raw_run(raw_run_directory: Path, processed_root: Path) -> dict[str, Any]:
    """Create a wide country-year table and a transparent data-quality report."""
    manifest_path = raw_run_directory / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing raw-run manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = manifest["run_id"]

    country_records = [
        record
        for payload in read_api_pages(raw_run_directory / "countries")
        for record in payload[1]
    ]
    countries = {
        record["id"]: _country_dimension(record)
        for record in country_records
        if is_country_or_economy(record)
    }
    all_entity_ids = {record["id"] for record in country_records}
    if not countries:
        raise ValueError("No countries were found after aggregate filtering")

    measure_columns = [indicator.column_name for indicator in INDICATORS]
    rows_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for country_code, country in countries.items():
        for year in range(START_YEAR, END_YEAR + 1):
            rows_by_key[(country_code, year)] = {**country, "year": year, **dict.fromkeys(measure_columns)}

    quality: dict[str, Any] = {
        "run_id": run_id,
        "country_count": len(countries),
        "aggregate_count": len(country_records) - len(countries),
        "expected_country_year_rows": len(rows_by_key),
        "duplicate_country_year_indicator_keys": [],
        "unmapped_entity_ids": [],
        "invalid_value_records": [],
        "aggregate_observations_skipped": 0,
        "missing_observations_by_indicator": {},
    }

    for indicator in INDICATORS:
        seen_keys: set[tuple[str, int]] = set()
        for payload in read_api_pages(raw_run_directory / "indicators" / indicator.code):
            for record in payload[1]:
                observed_indicator = (record.get("indicator") or {}).get("id")
                if observed_indicator != indicator.code:
                    raise ValueError(
                        f"Indicator mismatch in {indicator.code}: received {observed_indicator}"
                    )
                country_code = record.get("countryiso3code")
                if not country_code:
                    quality["aggregate_observations_skipped"] += 1
                    continue
                if country_code not in countries:
                    if country_code in all_entity_ids:
                        quality["aggregate_observations_skipped"] += 1
                        continue
                    quality["unmapped_entity_ids"].append(country_code)
                    continue
                try:
                    year = int(record["date"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid year for {indicator.code}: {record.get('date')}") from exc
                if not START_YEAR <= year <= END_YEAR:
                    raise ValueError(f"Out-of-scope year for {indicator.code}: {year}")
                key = (country_code, year)
                if key in seen_keys:
                    quality["duplicate_country_year_indicator_keys"].append(
                        {"indicator": indicator.code, "country_code": country_code, "year": year}
                    )
                    continue
                seen_keys.add(key)

                value = record.get("value")
                if value is not None:
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        quality["invalid_value_records"].append(
                            {"indicator": indicator.code, "country_code": country_code, "year": year, "value": value}
                        )
                        continue
                    if not _is_valid_value(indicator.code, value):
                        quality["invalid_value_records"].append(
                            {"indicator": indicator.code, "country_code": country_code, "year": year, "value": value}
                        )
                        continue
                    rows_by_key[key][indicator.column_name] = value

        quality["missing_observations_by_indicator"][indicator.code] = sum(
            1 for row in rows_by_key.values() if row[indicator.column_name] is None
        )

    if quality["duplicate_country_year_indicator_keys"]:
        raise ValueError("Duplicate country-year-indicator keys found in raw data")
    if quality["unmapped_entity_ids"]:
        raise ValueError("Unmapped entity IDs found in raw data")
    if quality["invalid_value_records"]:
        raise ValueError("Invalid indicator values found in raw data")

    quality["status"] = "passed_with_missing_values"
    fieldnames = [
        "country_code",
        "country_name",
        "region_id",
        "region_name",
        "income_level_id",
        "income_level_name",
        "year",
        *measure_columns,
    ]

    staging_directory = processed_root / f".{run_id}.staging"
    final_directory = processed_root / run_id
    if staging_directory.exists() or final_directory.exists():
        raise FileExistsError(f"Processed run already exists: {final_directory}")
    ordered_rows = [rows_by_key[key] for key in sorted(rows_by_key)]
    write_csv_atomic(staging_directory / "country_year.csv", ordered_rows, fieldnames)
    write_json_atomic(staging_directory / "data_quality_report.json", quality)
    write_json_atomic(staging_directory / "run_manifest.json", manifest)
    staging_directory.replace(final_directory)

    summary = {
        "run_id": run_id,
        "raw_run_directory": str(raw_run_directory),
        "processed_run_directory": str(final_directory),
        "country_year_rows": len(ordered_rows),
        "quality_status": quality["status"],
    }
    write_json_atomic(processed_root / "latest_run.json", summary)
    return summary
