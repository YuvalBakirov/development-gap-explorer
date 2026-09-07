"""Raw extraction layer. It stores each API page unchanged for reproducibility."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.settings import END_YEAR, INDICATORS, START_YEAR, WORLD_BANK_SOURCE_ID
from src.world_bank_api import WorldBankClient


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary_path.replace(path)


def is_country_or_economy(country_metadata: dict[str, Any]) -> bool:
    """Exclude World Bank aggregate entities using the API's own metadata."""
    region = country_metadata.get("region") or {}
    return region.get("id") not in {"", "NA", None} and region.get("value") != "Aggregates"


def fetch_resource_to_directory(
    client: WorldBankClient,
    resource: str,
    params: dict[str, Any],
    destination: Path,
) -> dict[str, Any]:
    first_page = client.get_page(resource, params, page=1)
    first_metadata = first_page[0]
    total_pages = int(first_metadata["pages"])
    page_row_counts: list[int] = []

    for page_number in range(1, total_pages + 1):
        payload = first_page if page_number == 1 else client.get_page(resource, params, page_number)
        metadata, rows = payload
        if int(metadata["page"]) != page_number or int(metadata["pages"]) != total_pages:
            raise ValueError(f"Pagination changed while extracting {resource}")
        write_json_atomic(destination / f"page_{page_number:03d}.json", payload)
        page_row_counts.append(len(rows))

    if sum(page_row_counts) != int(first_metadata["total"]):
        raise ValueError(f"Row count mismatch while extracting {resource}")

    return {
        "resource": resource,
        "pages": total_pages,
        "page_row_counts": page_row_counts,
        "total_rows": sum(page_row_counts),
        "reported_total": int(first_metadata["total"]),
        "last_updated": first_metadata.get("lastupdated"),
    }


def extract_world_bank_raw_data(client: WorldBankClient, raw_root: Path) -> dict[str, Any]:
    """Download all configured raw data into one timestamped, immutable run folder."""
    raw_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%S%fZ")
    run_directory = raw_root / run_id
    staging_directory = raw_root / f".{run_id}.staging"
    if run_directory.exists() or staging_directory.exists():
        raise FileExistsError(f"Raw-data run already exists: {run_directory}")

    countries_summary = fetch_resource_to_directory(
        client,
        "country",
        {"format": "json"},
        staging_directory / "countries",
    )
    country_pages = sorted((staging_directory / "countries").glob("page_*.json"))
    country_records = [
        record
        for page_path in country_pages
        for record in json.loads(page_path.read_text(encoding="utf-8"))[1]
    ]
    countries = [record for record in country_records if is_country_or_economy(record)]
    aggregates = [record for record in country_records if not is_country_or_economy(record)]

    indicator_summaries = []
    for indicator in INDICATORS:
        summary = fetch_resource_to_directory(
            client,
            f"country/all/indicator/{indicator.code}",
            {
                "format": "json",
                "date": f"{START_YEAR}:{END_YEAR}",
                "source": WORLD_BANK_SOURCE_ID,
            },
            staging_directory / "indicators" / indicator.code,
        )
        summary.update(
            {
                "indicator_code": indicator.code,
                "column_name": indicator.column_name,
                "required_for_core_analysis": indicator.required_for_core_analysis,
            }
        )
        indicator_summaries.append(summary)

    manifest = {
        "run_id": run_id,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "period": {"start_year": START_YEAR, "end_year": END_YEAR},
        "country_metadata": {
            **countries_summary,
            "countries": len(countries),
            "aggregates": len(aggregates),
            "country_rule": "region.id is neither empty nor NA and region.value is not Aggregates",
        },
        "indicators": indicator_summaries,
    }
    write_json_atomic(staging_directory / "manifest.json", manifest)
    staging_directory.replace(run_directory)
    write_json_atomic(raw_root / "latest_run.json", manifest)
    return manifest
