"""Main entry point for the Development Gap Explorer data pipeline.

It downloads and validates complete raw API pages, then transforms them into a
country-year analytical table, validates quality, and calculates descriptive
business metrics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.extraction import extract_world_bank_raw_data, write_json_atomic
from src.metrics import build_country_progress
from src.settings import processed_data_root, raw_data_root
from src.transformation import transform_raw_run
from src.world_bank_api import WorldBankApiError, WorldBankClient


def main() -> int:
    try:
        manifest = extract_world_bank_raw_data(WorldBankClient(), raw_data_root())
        summary = transform_raw_run(
            raw_data_root() / manifest["run_id"], processed_data_root(), publish_latest=False
        )
        metrics_summary = build_country_progress(
            Path(summary["processed_run_directory"]) / "country_year.csv",
            Path(summary["processed_run_directory"]),
            manifest["period"]["start_year"],
            manifest["period"]["end_year"],
        )
        write_json_atomic(processed_data_root() / "latest_run.json", summary)
    except (WorldBankApiError, OSError, ValueError) as exc:
        print(f"ETL extraction failed: {exc}", file=sys.stderr)
        return 1

    summary_path = processed_data_root() / "etl_run_summary.json"
    result = {"extraction": manifest, "transformation": summary, "metrics": metrics_summary}
    write_json_atomic(summary_path, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Raw data written to: {raw_data_root() / manifest['run_id']}")
    print(f"ETL summary written to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
