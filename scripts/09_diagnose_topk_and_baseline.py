from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "src"))
from recommender.config import resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose near-zero ALS Top-K metrics and compare against Popularity / Weighted baselines."
    )
    parser.add_argument(
        "--model-dir",
        default="models/als_full_iter_20260922_120859",
        help="Path to the full trained ALS model directory.",
    )
    parser.add_argument(
        "--catalog",
        default="artifacts/catalog/movie_catalog.parquet",
        help="Path to the aggregated movie catalog Parquet.",
    )
    parser.add_argument(
        "--ratings-train",
        default="data/full_interim/train.parquet",
        help="Path to full train ratings Parquet.",
    )
    parser.add_argument(
        "--ratings-valid",
        default="data/full_interim/valid.parquet",
        help="Path to full validation ratings Parquet.",
    )
    parser.add_argument(
        "--ratings-test",
        default="data/full_interim/test.parquet",
        help="Path to full test ratings Parquet.",
    )
    parser.add_argument(
        "--report-dir",
        default="reports/tables",
        help="Directory to write diagnostic tables and JSON report.",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--relevance-threshold", type=float, default=4.0)
    parser.add_argument(
        "--eval-user-sample",
        type=int,
        default=10000,
        help="Deterministic sample of eligible test users for fast matrix comparison (0 = all users).",
    )
    return parser.parse_args()


def compute_ranking_metrics_for_method(
    user_ids: np.ndarray,
    item_ids: np.ndarray,
    scores_matrix: np.ndarray,
    seen_by_user: dict[int, set[int]],
    relevant_by_user: dict[int, set[int]],
    top_k: int,
) -> dict[str, float]:
    """Compute Precision@K, Recall@K, NDCG@K, and recommendation count statistics."""
    precisions: list[float] = []
    recalls: list[float] = []
    ndcgs: list[float] = []
    rec_counts: list[int] = []

    discount = np.array([1.0 / math.log2(r + 2.0) for r in range(top_k)], dtype=np.float64)

    for row_idx, uid in enumerate(user_ids):
        uid_int = int(uid)
        rel_set = relevant_by_user.get(uid_int)
        if not rel_set:
            continue
        seen_set = seen_by_user.get(uid_int, set())
        row_scores = scores_matrix[row_idx]

        # Take top candidate indices (top_k + len(seen_set) bounded)
        cand_limit = min(len(item_ids), max(top_k + len(seen_set) + 5, 100))
        top_cand_idx = np.argpartition(-row_scores, cand_limit - 1)[:cand_limit]
        # Sort candidates by (-score, movieId)
        cand_scores = row_scores[top_cand_idx]
        cand_movies = item_ids[top_cand_idx]
        order = np.lexsort((cand_movies, -cand_scores))

        chosen: list[int] = []
        for idx in top_cand_idx[order]:
            mid = int(item_ids[idx])
            if mid not in seen_set:
                chosen.append(mid)
                if len(chosen) == top_k:
                    break

        rec_counts.append(len(chosen))
        hits = 0
        dcg = 0.0
        for rank_idx, mid in enumerate(chosen):
            if mid in rel_set:
                hits += 1
                dcg += float(discount[rank_idx])

        ideal_len = min(len(rel_set), top_k)
        idcg = float(np.sum(discount[:ideal_len])) if ideal_len > 0 else 0.0

        precisions.append(hits / float(top_k))
        recalls.append(hits / float(len(rel_set)))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

    return {
        "evaluated_users": len(precisions),
        "users_with_full_k_pct": float(sum(1 for c in rec_counts if c == top_k) / len(rec_counts))
        if rec_counts
        else 0.0,
        "min_recs_per_user": int(min(rec_counts)) if rec_counts else 0,
        "mean_recs_per_user": float(np.mean(rec_counts)) if rec_counts else 0.0,
        "precision_at_k": float(np.mean(precisions)) if precisions else 0.0,
        "recall_at_k": float(np.mean(recalls)) if recalls else 0.0,
        "ndcg_at_k": float(np.mean(ndcgs)) if ndcgs else 0.0,
    }


def evaluate_static_ranking(
    user_ids: np.ndarray,
    ranked_movie_ids: np.ndarray,
    seen_by_user: dict[int, set[int]],
    relevant_by_user: dict[int, set[int]],
    top_k: int,
) -> dict[str, float]:
    """Evaluate a global static ranking (Popularity or Weighted Score) with per-user seen filtering."""
    precisions: list[float] = []
    recalls: list[float] = []
    ndcgs: list[float] = []
    discount = [1.0 / math.log2(r + 2.0) for r in range(top_k)]

    for uid in user_ids:
        uid_int = int(uid)
        rel_set = relevant_by_user.get(uid_int)
        if not rel_set:
            continue
        seen_set = seen_by_user.get(uid_int, set())
        chosen: list[int] = []
        for mid in ranked_movie_ids:
            mid_int = int(mid)
            if mid_int not in seen_set:
                chosen.append(mid_int)
                if len(chosen) == top_k:
                    break

        hits = 0
        dcg = 0.0
        for rank_idx, mid in enumerate(chosen):
            if mid in rel_set:
                hits += 1
                dcg += discount[rank_idx]

        ideal_len = min(len(rel_set), top_k)
        idcg = sum(discount[:ideal_len]) if ideal_len > 0 else 0.0

        precisions.append(hits / float(top_k))
        recalls.append(hits / float(len(rel_set)))
        ndcgs.append(dcg / idcg if idcg > 0 else 0.0)

    return {
        "evaluated_users": len(precisions),
        "users_with_full_k_pct": 1.0,
        "min_recs_per_user": top_k,
        "mean_recs_per_user": float(top_k),
        "precision_at_k": float(np.mean(precisions)) if precisions else 0.0,
        "recall_at_k": float(np.mean(recalls)) if recalls else 0.0,
        "ndcg_at_k": float(np.mean(ndcgs)) if ndcgs else 0.0,
    }


def main() -> int:
    args = parse_args()
    started = time.perf_counter()

    model_dir = resolve_path(args.model_dir)
    catalog_path = resolve_path(args.catalog)
    train_path = resolve_path(args.ratings_train)
    valid_path = resolve_path(args.ratings_valid)
    test_path = resolve_path(args.ratings_test)
    report_dir = resolve_path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    print("1. Loading catalog and ALS demo recommendations...")
    catalog = pd.read_parquet(catalog_path)
    recs_path = model_dir / "recommendations" / "recommendations.parquet"
    recs = pd.read_parquet(recs_path)

    # Merge recommendations with catalog stats
    recs_enriched = recs.merge(
        catalog[["movieId", "rating_count", "avg_rating", "weighted_score"]],
        on="movieId",
        how="left",
    )
    recs_enriched["rating_count"] = recs_enriched["rating_count"].fillna(0).astype(int)

    # Per-user recommendation count check (§6.2)
    user_rec_counts = recs.groupby("userId")["movieId"].count()
    demo_user_ids = set(recs["userId"].unique().tolist())

    # Check seen-history overlap for the 500 demo users (§6.1)
    train_demo = pd.read_parquet(
        train_path,
        columns=["userId", "movieId"],
        filters=[("userId", "in", list(demo_user_ids))],
    )
    valid_demo = pd.read_parquet(
        valid_path,
        columns=["userId", "movieId"],
        filters=[("userId", "in", list(demo_user_ids))],
    )
    seen_demo_pairs = set(
        zip(train_demo["userId"].astype(int), train_demo["movieId"].astype(int))
    ) | set(zip(valid_demo["userId"].astype(int), valid_demo["movieId"].astype(int)))
    rec_demo_pairs = set(zip(recs["userId"].astype(int), recs["movieId"].astype(int)))
    seen_overlap_count = len(rec_demo_pairs & seen_demo_pairs)

    # Rating count distribution of ALS recommended items (§6.1)
    rc = recs_enriched["rating_count"]
    pred = recs_enriched["prediction"]
    top_frequent_als_movies = (
        recs_enriched.groupby(["movieId", "title"], as_index=False)
        .agg(
            recommended_times=("userId", "count"),
            mean_predicted_score=("prediction", "mean"),
            catalog_rating_count=("rating_count", "first"),
            catalog_avg_rating=("avg_rating", "first"),
        )
        .sort_values(["recommended_times", "mean_predicted_score"], ascending=[False, False])
        .head(10)
    )

    diagnostics_summary = {
        "demo_users_checked": int(len(user_rec_counts)),
        "total_demo_recommendation_rows": int(len(recs)),
        "min_recs_per_demo_user": int(user_rec_counts.min()),
        "max_recs_per_demo_user": int(user_rec_counts.max()),
        "users_with_full_10_recs": int((user_rec_counts == args.top_k).sum()),
        "seen_history_overlap_count": int(seen_overlap_count),
        "recommended_item_rating_count_stats": {
            "min": int(rc.min()),
            "median": float(rc.median()),
            "mean": float(rc.mean()),
            "p90": float(rc.quantile(0.90)),
            "max": int(rc.max()),
            "pct_with_le_5_ratings": float((rc <= 5).mean() * 100.0),
            "pct_with_le_10_ratings": float((rc <= 10).mean() * 100.0),
            "pct_with_ge_100_ratings": float((rc >= 100).mean() * 100.0),
        },
        "predicted_score_stats": {
            "min": float(pred.min()),
            "median": float(pred.median()),
            "mean": float(pred.mean()),
            "max": float(pred.max()),
            "pct_above_5_stars": float((pred > 5.0).mean() * 100.0),
        },
        "top_10_most_recommended_als_movies": top_frequent_als_movies.to_dict(orient="records"),
    }

    print(
        f"   Seen overlap = {seen_overlap_count}, "
        f"Median rating_count of ALS Top-10 items = {rc.median():.1f}, "
        f"Items with <= 5 ratings = {(rc <= 5).mean() * 100:.2f}%, "
        f"Predictions > 5.0 = {(pred > 5.0).mean() * 100:.2f}%"
    )

    print("2. Loading ALS factors and evaluating Top-K baselines on test users...")
    user_factors_df = pd.read_parquet(model_dir / "model" / "factors" / "user_factors.parquet")
    item_factors_df = pd.read_parquet(model_dir / "model" / "factors" / "item_factors.parquet")

    catalog_items_set = set(item_factors_df["id"].astype(int).tolist())

    # Load test relevant rows (rating >= 4.0 and in catalog)
    test_df = pd.read_parquet(test_path, columns=["userId", "movieId", "rating"])
    test_rel = test_df[
        (test_df["rating"] >= args.relevance_threshold)
        & (test_df["movieId"].isin(catalog_items_set))
    ]

    relevant_by_user: dict[int, set[int]] = {}
    for uid, mid in zip(test_rel["userId"].astype(int), test_rel["movieId"].astype(int)):
        relevant_by_user.setdefault(uid, set()).add(mid)

    all_eligible_users = sorted(relevant_by_user.keys())
    if args.eval_user_sample > 0 and len(all_eligible_users) > args.eval_user_sample:
        rng = np.random.default_rng(42)
        sampled_users = sorted(
            rng.choice(all_eligible_users, size=args.eval_user_sample, replace=False).tolist()
        )
    else:
        sampled_users = all_eligible_users

    sampled_user_set = set(sampled_users)
    print(f"   Evaluating on {len(sampled_users):,} eligible test users (out of {len(all_eligible_users):,})...")

    # Load seen items (train + valid) for sampled users
    train_seen = pd.read_parquet(
        train_path,
        columns=["userId", "movieId"],
        filters=[("userId", "in", sampled_users)],
    )
    valid_seen = pd.read_parquet(
        valid_path,
        columns=["userId", "movieId"],
        filters=[("userId", "in", sampled_users)],
    )
    seen_by_user: dict[int, set[int]] = {}
    for df_part in (train_seen, valid_seen):
        for uid, mid in zip(df_part["userId"].astype(int), df_part["movieId"].astype(int)):
            if uid in sampled_user_set:
                seen_by_user.setdefault(uid, set()).add(mid)

    # Filter user_factors to sampled users
    uf_sub = user_factors_df[user_factors_df["id"].isin(sampled_user_set)].sort_values("id")
    eval_user_ids = uf_sub["id"].to_numpy(dtype=np.int32)
    U = np.vstack(uf_sub["features"].to_numpy()).astype(np.float32)

    # Item factors aligned with catalog
    if_sorted = item_factors_df.sort_values("id").merge(
        catalog[["movieId", "rating_count", "avg_rating", "weighted_score"]],
        left_on="id",
        right_on="movieId",
        how="left",
    )
    all_item_ids = if_sorted["id"].to_numpy(dtype=np.int32)
    V_all = np.vstack(if_sorted["features"].to_numpy()).astype(np.float32)

    # Method 1: Unfiltered Explicit ALS (all 77,409 items)
    print("   Computing Method 1: Raw Explicit ALS (all catalog items)...")
    scores_all = U @ V_all.T
    als_raw_metrics = compute_ranking_metrics_for_method(
        eval_user_ids, all_item_ids, scores_all, seen_by_user, relevant_by_user, args.top_k
    )
    del scores_all

    # Method 2: Support-Filtered ALS (items with rating_count >= 100)
    print("   Computing Method 2: Support-Filtered ALS (rating_count >= 100)...")
    mask_100 = (if_sorted["rating_count"].fillna(0) >= 100).to_numpy()
    item_ids_100 = all_item_ids[mask_100]
    V_100 = V_all[mask_100]
    scores_100 = U @ V_100.T
    als_filtered_100_metrics = compute_ranking_metrics_for_method(
        eval_user_ids, item_ids_100, scores_100, seen_by_user, relevant_by_user, args.top_k
    )
    del scores_100

    # Method 3: Support-Filtered ALS (items with rating_count >= 500)
    print("   Computing Method 3: Support-Filtered ALS (rating_count >= 500)...")
    mask_500 = (if_sorted["rating_count"].fillna(0) >= 500).to_numpy()
    item_ids_500 = all_item_ids[mask_500]
    V_500 = V_all[mask_500]
    scores_500 = U @ V_500.T
    als_filtered_500_metrics = compute_ranking_metrics_for_method(
        eval_user_ids, item_ids_500, scores_500, seen_by_user, relevant_by_user, args.top_k
    )
    del scores_500

    # Method 4: Popularity Top-K Baseline (by rating_count desc, avg_rating desc)
    print("   Computing Method 4: Popularity Baseline (rating_count desc)...")
    pop_ranked = (
        catalog[catalog["movieId"].isin(catalog_items_set)]
        .sort_values(["rating_count", "avg_rating", "movieId"], ascending=[False, False, True])[
            "movieId"
        ]
        .to_numpy(dtype=np.int32)
    )
    pop_metrics = evaluate_static_ranking(
        eval_user_ids, pop_ranked, seen_by_user, relevant_by_user, args.top_k
    )

    # Method 5: Weighted Score Top-K Baseline (m=100, CINE32 ranking formula)
    print("   Computing Method 5: Weighted Score Baseline (m=100)...")
    weighted_ranked = (
        catalog[catalog["movieId"].isin(catalog_items_set)]
        .sort_values(["weighted_score", "rating_count", "movieId"], ascending=[False, False, True])[
            "movieId"
        ]
        .to_numpy(dtype=np.int32)
    )
    weighted_metrics = evaluate_static_ranking(
        eval_user_ids, weighted_ranked, seen_by_user, relevant_by_user, args.top_k
    )

    comparison_rows = [
        {
            "method": "ALS Explicit (Toàn bộ catalog 77,409 phim)",
            "candidate_movies": int(len(all_item_ids)),
            **als_raw_metrics,
        },
        {
            "method": "ALS Explicit + Lọc ngưỡng (rating_count >= 100)",
            "candidate_movies": int(len(item_ids_100)),
            **als_filtered_100_metrics,
        },
        {
            "method": "ALS Explicit + Lọc ngưỡng (rating_count >= 500)",
            "candidate_movies": int(len(item_ids_500)),
            **als_filtered_500_metrics,
        },
        {
            "method": "Baseline Weighted Score (m=100, công thức CINE32)",
            "candidate_movies": int(len(weighted_ranked)),
            **weighted_metrics,
        },
        {
            "method": "Baseline Popularity (Theo số lượt đánh giá cao nhất)",
            "candidate_movies": int(len(pop_ranked)),
            **pop_metrics,
        },
    ]

    csv_path = report_dir / "topk_comparison.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0].keys()))
        writer.writeheader()
        writer.writerows(comparison_rows)

    full_report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_dir": str(model_dir),
        "top_k": args.top_k,
        "relevance_threshold": args.relevance_threshold,
        "total_eligible_test_users": len(all_eligible_users),
        "evaluated_user_sample": len(eval_user_ids),
        "diagnostics_section_6_1_and_6_2": diagnostics_summary,
        "comparison_section_6_3": comparison_rows,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    json_path = report_dir / "topk_diagnostics_and_baseline.json"
    json_path.write_text(json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== KẾT QUẢ SO SÁNH TOP-10 TRÊN TẬP TEST ===")
    for row in comparison_rows:
        print(
            f"- {row['method']} (ứng viên={row['candidate_movies']:,}): "
            f"Precision@10={row['precision_at_k']:.6f}, "
            f"Recall@10={row['recall_at_k']:.6f}, "
            f"NDCG@10={row['ndcg_at_k']:.6f}"
        )
    print(f"OK: Saved {csv_path} and {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
