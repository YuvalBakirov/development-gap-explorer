import unittest
from pathlib import Path
from unittest.mock import patch

import etl
from src.metrics import MetricsError


class EtlOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw_root = Path("raw-root")
        self.processed_root = Path("processed-root")
        self.manifest = {
            "run_id": "run-test",
            "period": {"start_year": 2010, "end_year": 2024},
        }
        self.summary = {
            "run_id": "run-test",
            "processed_run_directory": "processed-root/run-test",
        }

    @patch("etl.write_json_atomic")
    @patch("etl.build_country_progress", return_value={"country_count": 1})
    @patch("etl.transform_raw_run")
    @patch("etl.extract_world_bank_raw_data")
    @patch("etl.processed_data_root")
    @patch("etl.raw_data_root")
    def test_publishes_latest_only_after_metrics_succeed(
        self,
        raw_root,
        processed_root,
        extract,
        transform,
        metrics,
        write_json,
    ) -> None:
        raw_root.return_value = self.raw_root
        processed_root.return_value = self.processed_root
        extract.return_value = self.manifest
        transform.return_value = self.summary

        self.assertEqual(etl.main(), 0)
        transform.assert_called_once_with(
            self.raw_root / "run-test", self.processed_root, publish_latest=False
        )
        metrics.assert_called_once()
        write_json.assert_any_call(self.processed_root / "latest_run.json", self.summary)

    @patch("etl.write_json_atomic")
    @patch("etl.build_country_progress", side_effect=MetricsError("metrics failed"))
    @patch("etl.transform_raw_run")
    @patch("etl.extract_world_bank_raw_data")
    @patch("etl.processed_data_root")
    @patch("etl.raw_data_root")
    def test_does_not_publish_latest_when_metrics_fail(
        self,
        raw_root,
        processed_root,
        extract,
        transform,
        metrics,
        write_json,
    ) -> None:
        raw_root.return_value = self.raw_root
        processed_root.return_value = self.processed_root
        extract.return_value = self.manifest
        transform.return_value = self.summary

        self.assertEqual(etl.main(), 1)
        write_json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
