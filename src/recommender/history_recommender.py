"""Recommend unseen films from genres of movies explicitly marked as watched."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from recommender.genre_recommender import GENRE_MAP_EN_TO_VI


@dataclass
class HistoryRecommendations:
    movies: pd.DataFrame
    history: pd.DataFrame
    watched_count: int
    genres: list[dict[str, str | int]]
    strategy: str


class HistoryRecommender:
    def __init__(self, catalog: pd.DataFrame) -> None:
        self.catalog = catalog
        self.movie_index = pd.Index(catalog["movieId"].to_numpy())
        self.genre_names = sorted(GENRE_MAP_EN_TO_VI)
        genre_index = {name: position for position, name in enumerate(self.genre_names)}
        self.genre_matrix = np.zeros((len(catalog), len(self.genre_names)), dtype=np.float32)
        for row, genres in enumerate(catalog["genres"]):
            for genre in set(genres if genres is not None else []):
                if genre in genre_index:
                    self.genre_matrix[row, genre_index[genre]] = 1
        self.genre_sizes = self.genre_matrix.sum(axis=1)

    def recommend(self, watched_movie_ids: Sequence[int], limit: int = 12) -> HistoryRecommendations:
        # A movie contributes once to each of its genres, regardless of repeats.
        ids = list(dict.fromkeys(watched_movie_ids))
        positions = self.movie_index.get_indexer(ids)
        positions = positions[positions >= 0]
        counts = self.genre_matrix[positions].sum(axis=0)
        genres = sorted(
            [{"id": genre, "label": GENRE_MAP_EN_TO_VI[genre], "count": int(counts[index])}
             for index, genre in enumerate(self.genre_names) if counts[index] > 0],
            key=lambda item: (-int(item["count"]), str(item["id"])),
        )
        unseen = np.ones(len(self.catalog), dtype=bool)
        unseen[positions] = False
        supported = self.catalog["rating_count"].fillna(0).to_numpy() >= 100
        eligible = unseen & supported
        if not eligible.any():
            eligible = unseen
        scores = np.divide(
            self.genre_matrix @ counts,
            self.genre_sizes,
            out=np.zeros(len(self.catalog), dtype=np.float32),
            where=self.genre_sizes > 0,
        )
        personal = bool((eligible & (scores > 0)).any())
        if personal:
            eligible &= scores > 0
        candidates = self.catalog.loc[eligible].copy()
        candidates["_affinity"] = scores[eligible] if personal else 0
        movies = candidates.sort_values(
            ["_affinity", "weighted_score", "rating_count", "movieId"],
            ascending=[False, False, False, True], na_position="last",
        ).head(limit).copy()
        movies["rank"] = np.arange(1, len(movies) + 1)

        def reason(movie_genres) -> str:
            matched = [str(genre["label"]) for genre in genres if genre["id"] in movie_genres][:2]
            return "Vì bạn thường xem " + " · ".join(matched) if matched else "Được cộng đồng đánh giá cao"

        movies["recommendation_reason"] = [reason(value) for value in movies["genres"]]
        history = self.catalog.iloc[positions[-12:][::-1]].copy()
        return HistoryRecommendations(movies, history, len(positions), genres,
                                      "genre_history" if personal else "community_fallback")
