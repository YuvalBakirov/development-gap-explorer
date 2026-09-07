"""Reproducible feasibility check for the World Bank Indicators API.

This is intentionally separate from the future production ETL. It measures
coverage, missingness, metadata quality, pagination, and country-year join
viability for the proposed Development Gap Explorer.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://api.worldbank.org/v2"
START_YEAR = 2010
END_YEAR = 2024
PER_PAGE = 1_000  # Deliberately forces pagination for an explicit test.

INDICATORS = {
    "NY.GDP.PCAP.KD": "gdp_per_capita_constant_2015_usd",
    "NY.GDP.PCAP.KD.ZG": "gdp_per_capita_growth_annual_pct",
    "SL.UEM.TOTL.ZS": "unemployment_total_pct_total_labor_force",
    "SP.DYN.LE00.IN": "life_expectancy_at_birth_years",
    "SP.POP.TOTL": "population_total",
    "SE.SEC.ENRR": "school_enrollment_secondary_gross_pct",
}

CORE_JOIN = [
    "NY.GDP.PCAP.KD",
    "SL.UEM.TOTL.ZS",
    "SP.DYN.LE00.IN",
    "SP.POP.TOTL",
]


def request_json(path: str, params: dict[str, Any], retries: int = 3) -> Any:
    query = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/{path}?{query}"
    headers = {"User-Agent": "development-gap-explorer-feasibility/0.1"}
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=45
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {url}")
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"World Bank request failed after {retries} attempts: {url}") from last_error


def validate_envelope(payload: Any, label: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(payload, list) or len(payload) != 2:
        raise ValueError(f"Unexpected response envelope for {label}")
    metadata, rows = payload
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        raise ValueError(f"Unexpected metadata/data types for {label}")
    return metadata, rows


def fetch_paginated(
    path: str, params: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[int], dict[str, Any]]:
    first_payload = request_json(path, {**params, "page": 1, "per_page": PER_PAGE})
    first_meta, first_rows = validate_envelope(first_payload, path)
    pages = int(first_meta["pages"])
    rows = list(first_rows)
    page_counts = [len(first_rows)]
    raw_pages = [first_payload]
    for page in range(2, pages + 1):
        payload = request_json(path, {**params, "page": page, "per_page": PER_PAGE})
        meta, page_rows = validate_envelope(payload, path)
        if int(meta["page"]) != page or int(meta["pages"]) != pages:
            raise ValueError(f"Pagination metadata changed while reading {path}")
        rows.extend(page_rows)
        page_counts.append(len(page_rows))
        raw_pages.append(payload)
    return rows, raw_pages, page_counts, first_meta


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def pct(numerator: int, denominator: int) -> float:
    return round((100.0 * numerator / denominator), 2) if denominator else 0.0


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    raw_dir = repo_root / "data" / "raw" / "feasibility_spike"
    output_dir = repo_root / "data" / "processed" / "feasibility_spike"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    country_rows, country_raw_pages, country_page_counts, country_response_meta = fetch_paginated(
        "country", {"format": "json"}
    )
    write_json(raw_dir / "countries_page_1.json", country_raw_pages[0])

    country_by_id = {row["id"]: row for row in country_rows}
    country_ids = {
        row["id"]
        for row in country_rows
        if (row.get("region") or {}).get("id") not in {"", "NA", None}
        and (row.get("region") or {}).get("value") != "Aggregates"
    }
    aggregate_ids = set(country_by_id) - country_ids

    observations: dict[str, dict[tuple[str, int], float]] = {}
    coverage_rows: list[dict[str, Any]] = []
    indicator_summary_rows: list[dict[str, Any]] = []
    metadata_rows: list[dict[str, Any]] = []
    pagination_rows: list[dict[str, Any]] = [
        {
            "resource": "countries",
            "pages": len(country_raw_pages),
            "page_counts": country_page_counts,
            "total_rows": len(country_rows),
            "reported_total": int(country_response_meta["total"]),
            "last_updated": country_response_meta.get("lastupdated"),
        }
    ]
    data_quality: dict[str, Any] = {
        "duplicate_keys": {},
        "unmapped_entity_ids": {},
        "observation_status_counts": {},
    }

    for indicator_id, slug in INDICATORS.items():
        indicator_meta_payload = request_json(
            f"indicator/{indicator_id}", {"format": "json", "per_page": 100}
        )
        _, indicator_meta = validate_envelope(indicator_meta_payload, f"indicator/{indicator_id}")
        if len(indicator_meta) != 1:
            raise ValueError(f"Expected one metadata row for {indicator_id}")
        meta = indicator_meta[0]
        metadata_rows.append(
            {
                "indicator_id": indicator_id,
                "requested_slug": slug,
                "name": meta.get("name"),
                "unit": meta.get("unit"),
                "source_id": (meta.get("source") or {}).get("id"),
                "source_name": (meta.get("source") or {}).get("value"),
                "source_note": meta.get("sourceNote"),
                "source_organization": meta.get("sourceOrganization"),
            }
        )
        write_json(raw_dir / f"indicator_metadata_{indicator_id}.json", indicator_meta_payload)

        rows, raw_pages, page_counts, response_meta = fetch_paginated(
            f"country/all/indicator/{indicator_id}",
            {"format": "json", "date": f"{START_YEAR}:{END_YEAR}"},
        )
        write_json(raw_dir / f"observations_{indicator_id}_page_1.json", raw_pages[0])
        pagination_rows.append(
            {
                "resource": indicator_id,
                "pages": len(raw_pages),
                "page_counts": page_counts,
                "total_rows": len(rows),
                "reported_total": int(response_meta["total"]),
                "last_updated": response_meta.get("lastupdated"),
            }
        )

        key_counts: dict[tuple[str, int], int] = defaultdict(int)
        non_null: dict[tuple[str, int], float] = {}
        unmapped_ids: set[str] = set()
        observation_status_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            entity_id = row.get("countryiso3code")
            year = int(row["date"])
            if entity_id and entity_id not in country_by_id:
                unmapped_ids.add(entity_id)
            if entity_id in country_ids:
                key = (entity_id, year)
                key_counts[key] += 1
                if row.get("value") is not None:
                    non_null[key] = row["value"]
                    status = str(row.get("obs_status") or "blank")
                    observation_status_counts[status] += 1

        duplicates = {f"{k[0]}:{k[1]}": v for k, v in key_counts.items() if v > 1}
        data_quality["duplicate_keys"][indicator_id] = duplicates
        data_quality["unmapped_entity_ids"][indicator_id] = sorted(unmapped_ids)
        data_quality["observation_status_counts"][indicator_id] = dict(
            sorted(observation_status_counts.items())
        )
        observations[indicator_id] = non_null

        expected = len(country_ids) * (END_YEAR - START_YEAR + 1)
        years_present = sorted({year for _, year in non_null})
        countries_present = {country for country, _ in non_null}
        for year in range(START_YEAR, END_YEAR + 1):
            year_count = sum(1 for _, observed_year in non_null if observed_year == year)
            coverage_rows.append(
                {
                    "indicator_id": indicator_id,
                    "year": year,
                    "non_null_countries": year_count,
                    "eligible_countries": len(country_ids),
                    "coverage_pct": pct(year_count, len(country_ids)),
                }
            )
        indicator_summary_rows.append(
            {
                "indicator_id": indicator_id,
                "expected_country_years": expected,
                "non_null_observations": len(non_null),
                "coverage_pct": pct(len(non_null), expected),
                "missing_observations": expected - len(non_null),
                "countries_with_any_value": len(countries_present),
                "first_observed_year": min(years_present) if years_present else None,
                "last_observed_year": max(years_present) if years_present else None,
            }
        )

    all_country_years = {
        (country_id, year)
        for country_id in country_ids
        for year in range(START_YEAR, END_YEAR + 1)
    }
    core_complete = set.intersection(*(set(observations[i]) for i in CORE_JOIN))
    five_complete = set.intersection(
        *(set(observations[i]) for i in [*CORE_JOIN, "NY.GDP.PCAP.KD.ZG"])
    )
    all_complete = set.intersection(*(set(values) for values in observations.values()))

    join_summary = {
        "join_key": ["countryiso3code", "year"],
        "eligible_country_year_grid": len(all_country_years),
        "core_indicators": CORE_JOIN,
        "core_complete_rows": len(core_complete),
        "core_complete_pct": pct(len(core_complete), len(all_country_years)),
        "core_plus_growth_complete_rows": len(five_complete),
        "core_plus_growth_complete_pct": pct(len(five_complete), len(all_country_years)),
        "all_six_complete_rows": len(all_complete),
        "all_six_complete_pct": pct(len(all_complete), len(all_country_years)),
        "countries_with_any_core_complete_row": len({c for c, _ in core_complete}),
        "countries_with_all_15_core_rows": sum(
            1
            for country_id in country_ids
            if all((country_id, year) in core_complete for year in range(START_YEAR, END_YEAR + 1))
        ),
    }

    entity_summary = {
        "metadata_rows": len(country_rows),
        "countries": len(country_ids),
        "aggregates": len(aggregate_ids),
        "country_rule": "region.id is neither empty nor 'NA', and region.value is not 'Aggregates'",
        "aggregate_rule": "all remaining country-metadata entities, normally region.id == 'NA'",
        "country_ids": sorted(country_ids),
        "aggregate_ids": sorted(aggregate_ids),
        "country_metadata_pages": len(country_raw_pages),
        "country_metadata_page_counts": country_page_counts,
    }

    write_json(output_dir / "entity_summary.json", entity_summary)
    write_json(output_dir / "indicator_metadata.json", metadata_rows)
    write_json(output_dir / "indicator_coverage_summary.json", indicator_summary_rows)
    write_json(output_dir / "pagination_summary.json", pagination_rows)
    write_json(output_dir / "join_viability.json", join_summary)
    write_json(output_dir / "data_quality.json", data_quality)
    write_json(
        output_dir / "run_metadata.json",
        {
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "api_base_url": BASE_URL,
            "period": {"start_year": START_YEAR, "end_year": END_YEAR},
            "requested_indicators": list(INDICATORS),
            "per_page": PER_PAGE,
        },
    )

    fieldnames = sorted({key for row in coverage_rows for key in row})
    with (output_dir / "coverage_by_indicator_year.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(coverage_rows)

    print(json.dumps({
        "period": f"{START_YEAR}-{END_YEAR}",
        "entities": entity_summary,
        "metadata": metadata_rows,
        "pagination": pagination_rows,
        "join_viability": join_summary,
        "data_quality": data_quality,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
