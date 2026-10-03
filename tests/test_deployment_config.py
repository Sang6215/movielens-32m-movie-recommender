from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
from threading import Barrier
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import web_api


class DeploymentConfigTests(unittest.TestCase):
    def test_concurrent_first_requests_share_one_catalog_and_model_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('factors_and_history.npz', 'manifest.json', 'catalog.parquet'):
                (root / name).touch()
            catalog = object()
            model = object()
            web_api._load_catalog.cache_clear()
            web_api._load_als.cache_clear()
            self.addCleanup(web_api._load_catalog.cache_clear)
            self.addCleanup(web_api._load_als.cache_clear)

            def slow_return(value):
                time.sleep(0.03)
                return value

            def first_requests(load):
                barrier = Barrier(4)
                def call(_):
                    barrier.wait(timeout=5)
                    return load()
                with ThreadPoolExecutor(max_workers=4) as pool:
                    return list(pool.map(call, range(4)))

            with patch.object(web_api, 'CATALOG_PATH', root / 'catalog.parquet'), patch.object(web_api, 'ALS_DIR', root), patch.object(web_api.pd, 'read_parquet', side_effect=lambda _: slow_return(catalog)) as read_catalog, patch.object(web_api, 'ALSRecommender', side_effect=lambda *_: slow_return(model)) as build_model:
                self.assertTrue(all(result is catalog for result in first_requests(web_api._catalog)))
                self.assertEqual(read_catalog.call_count, 1)
                self.assertTrue(all(result is model for result in first_requests(web_api._als)))
                self.assertEqual(build_model.call_count, 1)

    def test_cors_keeps_local_origins_and_normalizes_hosted_frontend(self) -> None:
        with patch.dict(os.environ, {"CINE32_CORS_ORIGINS": " https://cine32.example/,https://cine32.example "}):
            origins = web_api.configured_cors_origins()
        self.assertEqual(origins, ["http://127.0.0.1:5173", "http://localhost:5173", "https://cine32.example"])

    def test_cors_rejects_wildcards_credentials_and_urls_with_paths(self) -> None:
        for value in ("*", "https://cine32.example/movies", "https://user:password@cine32.example", "https://cine32.example?key=example"):
            with self.subTest(origin=value), patch.dict(os.environ, {"CINE32_CORS_ORIGINS": value}):
                with self.assertRaises(ValueError):
                    web_api.configured_cors_origins()

    def test_readiness_detects_missing_artifacts_without_loading_model_or_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "catalog.parquet"
            manifest = root / "catalog.json"
            als = root / "als"
            frontend = root / "dist"
            als.mkdir()
            frontend.mkdir()
            required = [catalog, manifest, als / "factors_and_history.npz", als / "manifest.json", frontend / "index.html"]
            with patch.object(web_api, "CATALOG_PATH", catalog), patch.object(web_api, "MANIFEST_PATH", manifest), patch.object(web_api, "ALS_DIR", als), patch.object(web_api, "DIST_DIR", frontend), patch.object(web_api, "TMDB_TOKEN", None), patch.object(web_api, "_als", side_effect=AssertionError("health must not load model")), TestClient(web_api.app) as client:
                self.assertEqual(client.get("/api/health").status_code, 503)
                for path in required:
                    path.touch()
                response = client.get("/api/health")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ready", "catalogReady": True, "alsReady": True, "frontendReady": True})
                for path in required:
                    path.unlink()
                    self.assertEqual(client.get("/api/health").status_code, 503)
                    path.touch()


if __name__ == "__main__":
    unittest.main()
