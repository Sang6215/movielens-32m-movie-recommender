"""Serve the exported Spark ALS factors without starting Spark per request."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class PersonalRecommendations:
    movies: pd.DataFrame
    history: pd.DataFrame
    known_user: bool
    history_count: int


class ALSRecommender:
    def __init__(self, artifact_dir: Path, catalog: pd.DataFrame) -> None:
        self.manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
        with np.load(artifact_dir / "factors_and_history.npz", allow_pickle=False) as data:
            self.user_ids = data["user_ids"]
            self.user_factors = data["user_factors"]
            item_ids = data["item_ids"]
            item_factors = data["item_factors"]
            self.history_ids = data["history_movie_ids"]
            self.history_ratings = data["history_ratings"]
            self.starts = data["history_starts"]
            self.ends = data["history_ends"]
        self.catalog = catalog.set_index("movieId", drop=False)
        supported = catalog.loc[catalog["rating_count"] >= self.manifest["min_rating_count"], "movieId"]
        candidates = np.isin(item_ids, supported.to_numpy())
        self.item_ids = item_ids[candidates]
        self.item_factors = item_factors[candidates]
        self.fallback_ids = catalog.loc[catalog["movieId"].isin(self.item_ids)].sort_values(
            ["weighted_score", "rating_count", "movieId"], ascending=[False, False, True]
        )["movieId"].to_numpy()

    def recommend(self, user_id: int, top_k: int = 10) -> PersonalRecommendations:
        index = int(np.searchsorted(self.user_ids, user_id))
        known = index < len(self.user_ids) and int(self.user_ids[index]) == user_id
        history = self.catalog.iloc[:0].copy()
        if not known:
            movies = self.catalog.loc[self.fallback_ids[:top_k]].copy()
            movies["prediction"] = None
            movies["rank"] = np.arange(1, len(movies) + 1)
            return PersonalRecommendations(movies, history, False, 0)

        start, end = int(self.starts[index]), int(self.ends[index])
        seen_ids = self.history_ids[start:end]
        seen_ratings = self.history_ratings[start:end]
        # History is already ordered by descending timestamp by the exporter.
        present = np.isin(seen_ids, self.catalog.index.to_numpy())
        history = self.catalog.loc[seen_ids[present][:12]].copy()
        history["history_rating"] = seen_ratings[present][:12]
        scores = self.item_factors @ self.user_factors[index]
        eligible = np.isfinite(scores) & ~np.isin(self.item_ids, seen_ids)
        ids, scores = self.item_ids[eligible], scores[eligible]
        order = np.lexsort((ids, -scores))[:top_k]
        movies = self.catalog.loc[ids[order]].copy()
        movies["prediction"] = scores[order]
        movies["rank"] = np.arange(1, len(movies) + 1)
        return PersonalRecommendations(movies, history, True, end - start)
