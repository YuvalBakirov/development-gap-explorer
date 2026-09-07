"""Create business metrics from the latest successful ETL run without re-downloading data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.metrics import MetricsError, build_country_progress
from src.settings import END_YEAR, START_YEAR, processed_data_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=START_YEAR)
    parser.add_argument("--end-year", type=int, default=END_YEAR)
    arguments = parser.parse_args()
    latest_path = processed_data_root() / "latest_run.json"
    if not latest_path.exists():
        raise MetricsError("No successful ETL run found. Run python etl.py first.")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    run_directory = Path(latest["processed_run_directory"])
    print(json.dumps(build_country_progress(run_directory / "country_year.csv", run_directory, arguments.start_year, arguments.end_year), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
