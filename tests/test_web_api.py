from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

import web_api


class MovieApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rows = [
            {
                "movieId": movie_id,
                "title": "Test Movie, The (2020)" if movie_id == 1 else f"Comedy {movie_id}",
                "year": 2020,
                "genres": ["Comedy"],
                "avg_rating": None if movie_id == 26 else 4.0,
                "rating_count": 0 if movie_id == 26 else 100,
                "weighted_score": float("nan") if movie_id == 26 else 5 - movie_id / 100,
                "tmdbId": None,
                "imdbId": None,
            }
            for movie_id in range(1, 27)
        ]
        rows.append(
            {
                "movieId": 27,
                "title": "Horror Only",
                "year": 2021,
                "genres": ["Horror"],
                "avg_rating": 5.0,
                "rating_count": 100,
                "weighted_score": 5.0,
                "tmdbId": None,
                "imdbId": None,
            }
        )
        cls.catalog = pd.DataFrame(rows)

    def test_genre_results_include_every_match_across_pages(self) -> None:
        with patch.object(web_api, "_catalog", return_value=self.catalog), patch.object(
            web_api.POSTER_LOADER, "snapshot", return_value=({}, set())
        ), TestClient(web_api.app) as client:
            first = client.get("/api/movies", params={"genres": "Comedy"})
            last = client.get("/api/movies", params={"genres": "Comedy", "page": 99})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["total"], 26)
        self.assertEqual(len(first.json()["items"]), 24)
        self.assertEqual(last.json()["page"], 2)
        self.assertEqual(last.json()["totalPages"], 2)
        self.assertEqual([item["movieId"] for item in last.json()["items"]], [25, 26])
        self.assertIsNone(last.json()["items"][-1]["rating"])

    def test_search_accepts_natural_article_order_and_genre(self) -> None:
        with patch.object(web_api, "_catalog", return_value=self.catalog), patch.object(
            web_api.POSTER_LOADER, "snapshot", return_value=({}, set())
        ), TestClient(web_api.app) as client:
            result = client.get(
                "/api/movies", params={"genres": "Comedy", "search": "The Test Movie"}
            )
            excluded = client.get(
                "/api/movies", params={"genres": "Horror", "search": "The Test Movie"}
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["total"], 1)
        self.assertEqual(result.json()["items"][0]["displayTitle"], "The Test Movie")
        self.assertEqual(excluded.json()["total"], 0)


if __name__ == "__main__":
    unittest.main()
