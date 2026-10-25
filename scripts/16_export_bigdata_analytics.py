"""Export small public aggregates for the website without copying private paths."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "reports" / "tables"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def build_analytics() -> dict:
    summary = read_csv(TABLES / "eda_summary.csv")[0]
    ratings = [{"label": row[""], "value": int(row["count"])} for row in read_csv(TABLES / "rating_distribution.csv")]
    genres = [{"label": row[""], "value": int(row["movie_count"])} for row in read_csv(TABLES / "genre_distribution.csv")]
    years = [{"label": row[""], "value": int(row["count"])} for row in read_csv(TABLES / "ratings_by_year.csv")]
    metrics = read_json(TABLES / "full_iter_20260922_120859" / "test_metrics.json")
    benchmark = read_json(TABLES / "bigdata_benchmarks.json")
    topk = read_json(TABLES / "topk_diagnostics_and_baseline.json")
    hdfs = read_json(TABLES / "hdfs_spark_verification.json")
    total = int(summary["ratings"])
    if sum(row["value"] for row in ratings) != total or sum(row["value"] for row in years) != total:
        raise ValueError("EDA distributions must add up to the original rating count")
    if metrics["fit_rows"] + metrics["test_rows"] != total:
        raise ValueError("Fit and test sizes do not match the source rating count")
    # Catalog size comes from the independently verified movies table, not the
    # smaller number of movies having at least one observed rating.
    movies = hdfs["other_tables"]["movies"]["rows"]
    return {
        "schemaVersion": 1,
        "snapshot": {
            "trainingDate": metrics["created_at_utc"][:10],
            "benchmarkDate": benchmark["created_at_utc"][:10],
            "hdfsDate": hdfs["created_at_utc"][:10],
            "kind": "offline_experiments",
        },
        "dataset": {
            "ratings": total, "users": int(summary["unique_users"]), "movies": movies,
            "ratedMovies": int(summary["unique_rated_movies"]),
            "tags": hdfs["other_tables"]["tags"]["rows"],
            "firstRating": summary["min_rating_time"], "lastRating": summary["max_rating_time"],
            "sparsity": 1 - total / (int(summary["unique_users"]) * movies),
            "ratingsDistribution": ratings, "genres": genres, "ratingsByYear": years,
        },
        "performance": {
            "storage": benchmark["storage_comparison"],
            "query": benchmark["format_query_benchmark"],
            "threads": benchmark["spark_thread_scaling"],
        },
        "model": {
            "trainRows": metrics["train_rows"], "validationRows": metrics["valid_rows"],
            "testRows": metrics["test_rows"], "fitRows": metrics["fit_rows"],
            "params": metrics["selected_params"], "test": metrics["test_rating_metrics"],
            "tuning": [{"iterations": int(row["maxIter"]), "rmse": float(row["rmse"]), "mae": float(row["mae"])}
                       for row in read_csv(TABLES / "full_iter_20260922_120859" / "als_tuning.csv")],
            "rankingUsers": topk["evaluated_user_sample"],
            "ranking": [{"label": label, "candidates": row["candidate_movies"],
                         "precision": row["precision_at_k"], "recall": row["recall_at_k"], "ndcg": row["ndcg_at_k"]}
                        for label, row in zip(
                            ["ALS toàn catalog", "ALS ≥100 lượt chấm", "ALS ≥500 lượt chấm", "Điểm cộng đồng có trọng số", "Phổ biến theo lượt chấm"],
                            topk["comparison_section_6_3"])],
        },
        "hdfs": {
            "date": hdfs["created_at_utc"][:10], "dataNodes": hdfs["live_datanodes"],
            "sparkMaster": hdfs["spark_master"], "sparkVersion": hdfs["spark_version"],
            "hadoopVersion": hdfs["hadoop_version"], "modelRetrained": hdfs["model_retrained"],
            "rawRows": hdfs["etl"]["raw_rows"], "readbackRows": hdfs["etl"]["parquet_rows_readback"],
            "invalidRows": hdfs["etl"]["invalid_rows"], "duplicates": hdfs["etl"]["duplicate_rows"],
            "success": hdfs["success"],
        },
        "sources": [
            {"label": "EDA và phân bố dữ liệu", "path": "reports/tables/eda_summary.csv"},
            {"label": "Phân bố điểm rating", "path": "reports/tables/rating_distribution.csv"},
            {"label": "Phim theo thể loại", "path": "reports/tables/genre_distribution.csv"},
            {"label": "Rating theo năm", "path": "reports/tables/ratings_by_year.csv"},
            {"label": "Benchmark CSV và Parquet", "path": "reports/tables/bigdata_benchmarks.json"},
            {"label": "Kết quả ALS full test", "path": "reports/tables/full_iter_20260922_120859/test_metrics.json"},
            {"label": "Chọn số vòng ALS", "path": "reports/tables/full_iter_20260922_120859/als_tuning.csv"},
            {"label": "Chẩn đoán và so sánh Top K", "path": "reports/tables/topk_diagnostics_and_baseline.json"},
            {"label": "Kiểm chứng Spark và HDFS", "path": "reports/tables/hdfs_spark_verification.json"},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "assets" / "bigdata_analytics.json")
    args = parser.parse_args()
    payload = build_analytics()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Exported {args.output.name}: {args.output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
