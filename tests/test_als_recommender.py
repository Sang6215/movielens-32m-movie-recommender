from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from recommender.als_recommender import ALSRecommender
import web_api


class ALSServingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        np.savez(root / "factors_and_history.npz",
                 user_ids=np.array([1, 2]), user_factors=np.array([[1, 0], [0, 1]], dtype=np.float32),
                 item_ids=np.array([10, 20, 30, 40, 50]),
                 item_factors=np.array([[4, 1], [5, 2], [3, 5], [3, 4], [9, 9]], dtype=np.float32),
                 history_movie_ids=np.array([20, 30]), history_ratings=np.array([5, 4]),
                 history_starts=np.array([0, 1]), history_ends=np.array([1, 2]))
        (root / "manifest.json").write_text(json.dumps({
            "min_rating_count": 100, "top_k": 10, "selected_params": {}, "test_rating_metrics": {},
        }))
        self.catalog = pd.DataFrame([{
            "movieId": mid, "title": f"Movie {mid}", "genres": ["Comedy"],
            "rating_count": 10 if mid == 50 else 100,
            "avg_rating": 4.0, "weighted_score": mid / 100,
        } for mid in (10, 20, 30, 40, 50)])
        self.engine = ALSRecommender(root, self.catalog)

    def test_factor_scores_seen_exclusion_support_and_stable_ties(self) -> None:
        result = self.engine.recommend(1)
        self.assertTrue(result.known_user)
        self.assertEqual(result.movies["movieId"].tolist(), [10, 30, 40])
        self.assertEqual(result.movies["prediction"].tolist(), [4, 3, 3])
        self.assertEqual(result.history["movieId"].tolist(), [20])
        self.assertEqual(result.history_count, 1)
        self.assertEqual(self.engine.recommend(2).movies["movieId"].tolist(), [40, 20, 10])

    def test_unknown_user_uses_community_ranking_without_als_score(self) -> None:
        result = self.engine.recommend(999)
        self.assertFalse(result.known_user)
        self.assertEqual(result.movies["movieId"].tolist(), [40, 30, 20, 10])
        self.assertTrue(result.movies["prediction"].isna().all())
        self.assertTrue(result.history.empty)

    def test_api_preserves_personal_scores_and_validates_user_id(self) -> None:
        with patch.object(web_api, "_als", return_value=self.engine), patch.object(
            web_api.POSTER_LOADER, "snapshot", return_value=({}, set())
        ), TestClient(web_api.app) as client:
            known = client.get("/api/als/recommendations", params={"user_id": 1}).json()
            unknown = client.get("/api/als/recommendations", params={"user_id": 0}).json()
            invalid = client.get("/api/als/recommendations", params={"user_id": -1})
        self.assertEqual(known["strategy"], "als")
        self.assertEqual(known["items"][0]["predictionScore"], 4)
        self.assertEqual(known["items"][0]["personalRank"], 1)
        self.assertEqual(known["history"][0]["historyRating"], 5)
        self.assertEqual(unknown["strategy"], "weighted_score_fallback")
        self.assertIsNone(unknown["items"][0]["predictionScore"])
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
