from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import web_api


class AnalyticsTests(unittest.TestCase):
    def test_snapshot_conserves_source_rows_and_keeps_training_provenance(self) -> None:
        data = json.loads(web_api.ANALYTICS_PATH.read_text(encoding="utf-8"))
        source = data["dataset"]
        model = data["model"]
        self.assertEqual(source["ratings"], 32_000_204)
        self.assertEqual(source["movies"], 87_585)
        self.assertEqual(sum(row["value"] for row in source["ratingsDistribution"]), source["ratings"])
        self.assertEqual(sum(row["value"] for row in source["ratingsByYear"]), source["ratings"])
        self.assertEqual(model["trainRows"] + model["validationRows"], model["fitRows"])
        self.assertEqual(model["fitRows"] + model["testRows"], source["ratings"])
        self.assertAlmostEqual(model["test"]["rows"] / model["testRows"], model["test"]["coverage"])
        self.assertFalse(data["hdfs"]["modelRetrained"])
        self.assertEqual(data["hdfs"]["readbackRows"], source["ratings"])
        self.assertTrue(all(row["path"].startswith("reports/tables/") for row in data["sources"]))
        encoded = json.dumps(data, ensure_ascii=False)
        for private_value in ["C:\\Users", "D:\\", "TMDB_READ_ACCESS_TOKEN"]:
            self.assertNotIn(private_value, encoded)
        def assert_aggregate(value):
            if isinstance(value, dict):
                self.assertTrue({"movieId", "userId", "watched"}.isdisjoint(value))
                for child in value.values():
                    assert_aggregate(child)
            elif isinstance(value, list):
                for child in value:
                    assert_aggregate(child)
        assert_aggregate(data)

    def test_exported_snapshot_matches_current_evidence(self) -> None:
        path = Path(__file__).resolve().parents[1] / "scripts/16_export_bigdata_analytics.py"
        spec = importlib.util.spec_from_file_location("analytics_export", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.build_analytics(), json.loads(web_api.ANALYTICS_PATH.read_text(encoding="utf-8")))

    def test_api_needs_no_catalog_model_or_raw_dataset(self) -> None:
        with patch.object(web_api, "_catalog", side_effect=AssertionError("analytics must not load catalog")), patch.object(
            web_api, "_als", side_effect=AssertionError("analytics must not load model")
        ), TestClient(web_api.app) as client:
            response = client.get("/api/analytics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["snapshot"]["kind"], "offline_experiments")
        self.assertEqual(response.json()["model"]["params"]["maxIter"], 20)

    def test_missing_snapshot_returns_unavailable_instead_of_spa_html(self) -> None:
        with tempfile.TemporaryDirectory() as folder, patch.object(web_api, "ANALYTICS_PATH", Path(folder) / "missing.json"), TestClient(web_api.app) as client:
            response = client.get("/api/analytics")
        self.assertEqual(response.status_code, 503)
        self.assertIn("detail", response.json())


if __name__ == "__main__":
    unittest.main()
