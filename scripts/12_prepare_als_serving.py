"""Export existing Spark ALS factors and complete rating history for the web API.

This is an inference artifact, not another training run. Serving excludes every
known rating (train/validation/test); offline test metrics retain their original
train+validation exclusion protocol.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", default="models/als_full_iter_20260922_120859")
    parser.add_argument("--history", default="data/processed/parquet/ratings.parquet")
    parser.add_argument("--catalog", default="artifacts/catalog/movie_catalog.parquet")
    parser.add_argument("--output-dir", default="artifacts/als_serving")
    parser.add_argument("--min-rating-count", type=int, default=100)
    args = parser.parse_args()
    if args.min_rating_count < 1:
        parser.error("--min-rating-count must be positive")
    model_dir, output_dir = ROOT / args.model_dir, ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    user_frame = pd.read_parquet(model_dir / "model/factors/user_factors.parquet").sort_values("id")
    item_frame = pd.read_parquet(model_dir / "model/factors/item_factors.parquet").sort_values("id")
    user_ids = user_frame["id"].to_numpy(dtype=np.int32)
    item_ids = item_frame["id"].to_numpy(dtype=np.int32)
    user_factors = np.stack(user_frame["features"].to_numpy()).astype(np.float32)
    item_factors = np.stack(item_frame["features"].to_numpy()).astype(np.float32)
    if user_factors.shape[1] != item_factors.shape[1] or not np.isfinite(user_factors).all() or not np.isfinite(item_factors).all():
        raise ValueError("Invalid ALS factors")
    print(f"Loaded {len(user_ids):,} users and {len(item_ids):,} item factors.", flush=True)
    history = pd.read_parquet(ROOT / args.history, columns=["userId", "movieId", "rating", "timestamp"])
    # Keep arrays compact and avoid retaining the entire pandas frame after sort.
    history_user_ids = history["userId"].to_numpy(dtype=np.int32)
    movie_ids = history["movieId"].to_numpy(dtype=np.int32)
    ratings = history["rating"].to_numpy(dtype=np.float32)
    timestamps = history["timestamp"].to_numpy(dtype=np.int64)
    del history
    order = np.lexsort((movie_ids, -timestamps, history_user_ids))
    history_user_ids = history_user_ids[order]
    starts = np.searchsorted(history_user_ids, user_ids, side="left")
    ends = np.searchsorted(history_user_ids, user_ids, side="right")
    history_rows = len(movie_ids)
    print(f"Indexed {history_rows:,} ratings. Saving inference artifact...", flush=True)
    target = output_dir / "factors_and_history.npz"
    temporary = output_dir / "factors_and_history.tmp"
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, user_ids=user_ids, user_factors=user_factors,
                            item_ids=item_ids, item_factors=item_factors,
                            history_movie_ids=movie_ids[order], history_ratings=ratings[order],
                            history_starts=starts, history_ends=ends)
    temporary.replace(target)
    metrics = json.loads((model_dir / "metrics.json").read_text(encoding="utf-8"))
    catalog = pd.read_parquet(ROOT / args.catalog, columns=["movieId", "rating_count"])
    candidates = catalog[(catalog["rating_count"] >= args.min_rating_count) & catalog["movieId"].isin(item_ids)]
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_model": args.model_dir,
        "history_source": args.history,
        "history_policy": "exclude_all_observed_ratings_including_test_for_live_demo",
        "history_rows": history_rows,
        "users": len(user_ids), "items": len(item_ids),
        "candidate_movies": len(candidates), "min_rating_count": args.min_rating_count,
        "selected_params": metrics["selected_params"],
        "test_rating_metrics": metrics["test_rating_metrics"],
        "top_k": 10,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ready: {len(candidates):,} candidate movies; no model retraining.")


if __name__ == "__main__":
    main()
