"""Main entry point for the Development Gap Explorer data pipeline.

It downloads and validates complete raw API pages, then transforms them into a
country-year analytical table with a data-quality report.
"""

from __future__ import annotations

import json
import sys

from src.extraction import extract_world_bank_raw_data, write_json_atomic
from src.settings import processed_data_root, raw_data_root
from src.transformation import transform_raw_run
from src.world_bank_api import WorldBankApiError, WorldBankClient


def main() -> int:
    try:
        manifest = extract_world_bank_raw_data(WorldBankClient(), raw_data_root())
        summary = transform_raw_run(
            raw_data_root() / manifest["run_id"], processed_data_root()
        )
    except (WorldBankApiError, OSError, ValueError) as exc:
        print(f"ETL extraction failed: {exc}", file=sys.stderr)
        return 1

    summary_path = processed_data_root() / "etl_run_summary.json"
    write_json_atomic(summary_path, {"extraction": manifest, "transformation": summary})
    print(json.dumps({"extraction": manifest, "transformation": summary}, indent=2, ensure_ascii=False))
    print(f"Raw data written to: {raw_data_root() / manifest['run_id']}")
    print(f"ETL summary written to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
