from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from recommender.history_recommender import HistoryRecommender
import web_api


class WatchedHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = pd.DataFrame([
            {"movieId": mid, "title": f"Movie {mid}", "genres": genres, "rating_count": count,
             "avg_rating": 4.0, "weighted_score": score, "tmdbId": None, "imdbId": None}
            for mid, genres, count, score in (
                (1, ["Action", "Comedy"], 200, 4.0),
                (2, ["Action"], 200, 4.0),
                (3, ["Comedy"], 200, 4.2),
                (4, ["Action"], 200, 4.0),
                (5, ["Romance"], 200, 4.9),
                (6, ["Action"], 1, 5.0),
                (7, ["IMAX", "(no genres listed)"], 200, 3.0),
                (8, ["Action"], 200, 4.0),
            )
        ])
        self.engine = HistoryRecommender(self.catalog)

    def test_unique_watches_count_each_genre_once_and_exclude_seen(self) -> None:
        result = self.engine.recommend([1, 1, 2, 999999])
        counts = {genre["id"]: genre["count"] for genre in result.genres}
        self.assertEqual(result.watched_count, 2)
        self.assertEqual(counts, {"Action": 2, "Comedy": 1})
        self.assertEqual(result.movies["movieId"].tolist(), [4, 8, 3])
        self.assertEqual(result.history["movieId"].tolist(), [2, 1])
        self.assertTrue(result.movies["recommendation_reason"].str.contains("bạn thường xem").all())

    def test_profiles_have_independent_recommendations_without_shared_mutation(self) -> None:
        before = self.catalog.copy(deep=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            action, romance = list(pool.map(self.engine.recommend, ([2], [5])))
        self.assertEqual(action.movies.iloc[0]["movieId"], 4)
        self.assertEqual(action.genres[0]["id"], "Action")
        self.assertEqual(romance.genres[0]["id"], "Romance")
        self.assertNotIn(5, romance.movies["movieId"].tolist())
        self.assertEqual(romance.strategy, "community_fallback")
        pd.testing.assert_frame_equal(before, self.catalog)

    def test_empty_or_unclassified_history_uses_community_and_all_watched_is_empty(self) -> None:
        self.assertEqual(self.engine.recommend([]).movies.iloc[0]["movieId"], 5)
        unclassified = self.engine.recommend([7])
        self.assertEqual(unclassified.genres, [])
        self.assertEqual(unclassified.watched_count, 1)
        self.assertNotIn(7, unclassified.movies["movieId"].tolist())
        exhausted = self.engine.recommend(self.catalog["movieId"].tolist())
        self.assertTrue(exhausted.movies.empty)

    def test_api_does_not_accept_client_genres_and_validates_input(self) -> None:
        with patch.object(web_api, "_history_recommender", return_value=self.engine), patch.object(web_api.POSTER_LOADER, "snapshot", return_value=({}, set())), TestClient(web_api.app) as client:
            result = client.post("/api/demo/recommendations", json={"movie_ids": [1, 2, 2]})
            self.assertEqual(result.status_code, 200)
            body = result.json()
            self.assertEqual(body["watchedCount"], 2)
            self.assertEqual(body["genres"][0], {"id": "Action", "label": "Hành động", "count": 2})
            self.assertTrue(all("predictionScore" not in movie for movie in body["items"]))
            for invalid in ({"movie_ids": [-1]}, {"movie_ids": [True]}, {"movie_ids": ["1"]}, {"movie_ids": [1] * 1001}, {"movie_ids": [1], "genres": ["Romance"]}):
                with self.subTest(body=invalid):
                    self.assertEqual(client.post("/api/demo/recommendations", json=invalid).status_code, 422)


if __name__ == "__main__":
    unittest.main()
