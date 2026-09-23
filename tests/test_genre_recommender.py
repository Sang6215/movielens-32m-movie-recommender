from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recommender.genre_recommender import recommend_by_genres


class GenreRecommenderTests(unittest.TestCase):
    def test_returns_every_matching_movie_including_unrated(self) -> None:
        rows = [
            {
                "movieId": movie_id,
                "title": f"Movie {movie_id}",
                "genres": ["Comedy"],
                "rating_count": 0 if movie_id == 31 else 100,
                "weighted_score": float("nan") if movie_id == 31 else 4.0,
            }
            for movie_id in range(1, 32)
        ]
        rows.append(
            {
                "movieId": 32,
                "title": "Unrelated",
                "genres": ["Horror"],
                "rating_count": 100,
                "weighted_score": 5.0,
            }
        )

        result = recommend_by_genres(pd.DataFrame(rows), ["Hài (Comedy)"])

        self.assertEqual(result.total_matched, 31)
        self.assertEqual(len(result.movies), 31)
        self.assertEqual(set(result.movies["movieId"]), set(range(1, 32)))
        self.assertEqual(result.movies.iloc[-1]["movieId"], 31)


if __name__ == "__main__":
    unittest.main()
