from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

project_root = Path(__file__).resolve().parents[1]
local_hadoop = project_root / ".hadoop"
if (local_hadoop / "bin" / "winutils.exe").exists():
    os.environ.setdefault("HADOOP_HOME", str(local_hadoop))
    os.environ.setdefault("hadoop.home.dir", str(local_hadoop))
    # Hadoop's Windows native library must be discoverable by both the JVM and
    # the local executor. Keeping this in the script makes checkpointing work
    # when the command is launched from a fresh PowerShell session.
    hadoop_bin = local_hadoop / "bin"
    os.environ["PATH"] = f"{hadoop_bin}{os.pathsep}{os.environ.get('PATH', '')}"
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS, ALSModel
from pyspark import StorageLevel
from pyspark.sql import DataFrame, SparkSession, functions as F, types as T
from pyspark.sql.window import Window

sys.path.append(str(project_root / "src"))
from recommender.config import resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tune ALS on validation, fit the selected model and evaluate Top-K on test."
    )
    parser.add_argument("--ratings-train", default="data/interim/train.parquet")
    parser.add_argument("--ratings-valid", default="data/interim/valid.parquet")
    parser.add_argument("--ratings-test", default="data/interim/test.parquet")
    parser.add_argument("--movies", default="data/processed/parquet/movies.parquet")
    parser.add_argument("--output-dir", default="models/als_final")
    parser.add_argument("--report-dir", default="reports/tables")
    parser.add_argument(
        "--grid",
        default="8:0.08:4,16:0.08:5,24:0.12:5",
        help="Comma-separated rank:regParam:maxIter configurations.",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=50)
    parser.add_argument("--relevance-threshold", type=float, default=4.0)
    parser.add_argument("--demo-users", type=int, default=200)
    parser.add_argument("--master", default="local[4]")
    parser.add_argument("--shuffle-partitions", type=int, default=32)
    parser.add_argument("--num-user-blocks", type=int, default=50)
    parser.add_argument("--num-item-blocks", type=int, default=50)
    parser.add_argument("--driver-memory", default="16g")
    parser.add_argument("--memory-overhead", default="2g")
    parser.add_argument(
        "--spark-local-dir",
        default=None,
        help="Directory for Spark shuffle/temp files; useful to place them on a larger disk.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=None,
        help="Local Spark checkpoint directory. Defaults to <output-dir>/_spark_checkpoints.",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=0,
        help="Checkpoint ALS lineage every N iterations; 0 disables local checkpointing (default: 0).",
    )
    return parser.parse_args()


def save_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_grid(raw: str) -> list[dict[str, int | float]]:
    grid: list[dict[str, int | float]] = []
    for value in raw.split(","):
        rank, reg_param, max_iter = value.strip().split(":")
        grid.append(
            {
                "rank": int(rank),
                "regParam": float(reg_param),
                "maxIter": int(max_iter),
            }
        )
    return grid


def build_spark(args: argparse.Namespace) -> SparkSession:
    builder = (
        SparkSession.builder.appName("movielens32m-als-evaluation")
        .master(args.master)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.memory", args.driver_memory)
        .config("spark.executor.memory", args.driver_memory)
        .config("spark.driver.memoryOverhead", args.memory_overhead)
        .config("spark.executor.memoryOverhead", args.memory_overhead)
        .config("spark.driver.maxResultSize", "4g")
        .config("spark.sql.shuffle.partitions", str(args.shuffle_partitions))
        .config("spark.sql.ansi.enabled", "false")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        # Large ALS iteration counts create a deep JVM call/serialization
        # stack on local Windows runs. Reserve more stack per Spark thread.
        .config("spark.driver.extraJavaOptions", "-Xss16m")
        .config("spark.executor.extraJavaOptions", "-Xss16m")
    )
    if args.spark_local_dir:
        local_dir = resolve_path(args.spark_local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        builder = builder.config("spark.local.dir", str(local_dir))
    return builder.getOrCreate()


def load_ratings(spark: SparkSession, path: str) -> DataFrame:
    return (
        spark.read.parquet(str(resolve_path(path)))
        .select(
            F.col("userId").cast("int"),
            F.col("movieId").cast("int"),
            F.col("rating").cast("float"),
        )
    )


def rating_metrics(model: ALSModel, frame: DataFrame) -> dict[str, float | int]:
    predictions = model.transform(frame).cache()
    rows = predictions.count()
    if rows == 0:
        predictions.unpersist()
        return {"rows": 0, "rmse": None, "mae": None, "coverage": 0.0}
    rmse = RegressionEvaluator(
        metricName="rmse", labelCol="rating", predictionCol="prediction"
    ).evaluate(predictions)
    mae = RegressionEvaluator(
        metricName="mae", labelCol="rating", predictionCol="prediction"
    ).evaluate(predictions)
    predictions.unpersist()
    total = frame.count()
    return {
        "rows": rows,
        "rmse": float(rmse),
        "mae": float(mae),
        "coverage": float(rows / total) if total else 0.0,
    }


def make_recommendations(
    model: ALSModel,
    users: DataFrame,
    seen: DataFrame,
    top_k: int,
    candidate_k: int,
) -> DataFrame:
    raw = model.recommendForUserSubset(users.select("userId").distinct(), candidate_k)
    flat = (
        raw.select("userId", F.posexplode("recommendations").alias("raw_rank", "rec"))
        .select(
            F.col("userId").cast("int"),
            F.col("rec.movieId").cast("int").alias("movieId"),
            F.col("rec.rating").cast("double").alias("score"),
        )
    )
    # Never recommend a movie already present in the fitting history.
    unseen = flat.join(seen.select("userId", "movieId").distinct(), ["userId", "movieId"], "left_anti")
    ordering = Window.partitionBy("userId").orderBy(F.desc("score"), F.asc("movieId"))
    return unseen.withColumn("rank", F.row_number().over(ordering)).where(F.col("rank") <= top_k)


def topk_metrics(
    model: ALSModel,
    fit_frame: DataFrame,
    test_frame: DataFrame,
    top_k: int,
    candidate_k: int,
    relevance_threshold: float,
) -> dict[str, float | int]:
    catalog = fit_frame.select("movieId").distinct()
    relevant_all = (
        test_frame.where(F.col("rating") >= relevance_threshold)
        .select("userId", "movieId")
        .distinct()
    )
    relevant = relevant_all.join(catalog, "movieId", "left_semi")
    relevant_users = relevant.select("userId").distinct()
    recs = make_recommendations(
        model,
        relevant_users,
        fit_frame.select("userId", "movieId"),
        top_k,
        candidate_k,
    ).cache()
    hits = recs.join(relevant, ["userId", "movieId"], "inner").cache()
    per_user = (
        relevant.groupBy("userId")
        .agg(F.count("movieId").alias("relevant_count"))
        .join(hits.groupBy("userId").agg(F.count("movieId").alias("hit_count")), "userId", "left")
        .join(
            hits.groupBy("userId")
            .agg(F.sum(1.0 / F.log2(F.col("rank") + F.lit(1.0))).alias("dcg")),
            "userId",
            "left",
        )
        .fillna({"hit_count": 0, "dcg": 0.0})
    )
    # Collect only one compact row per user (not the ratings or recommendations)
    # and calculate the final averages in Python. This avoids a Python UDF in a
    # Spark aggregation, which is fragile with Python 3.13 on Windows.
    user_rows = per_user.select("relevant_count", "hit_count", "dcg").collect()
    precision_values = [float(row["hit_count"]) / top_k for row in user_rows]
    recall_values = [float(row["hit_count"]) / float(row["relevant_count"]) for row in user_rows]
    ndcg_values: list[float] = []
    for row in user_rows:
        ideal = sum(
            1.0 / math.log2(index + 2.0)
            for index in range(min(int(row["relevant_count"]), top_k))
        )
        ndcg_values.append(float(row["dcg"]) / ideal if ideal else 0.0)
    relevant_total = relevant_all.count()
    relevant_in_catalog = relevant.count()
    user_count = relevant_users.count()
    users_with_recs = recs.select("userId").distinct().count()
    recs.unpersist()
    hits.unpersist()
    return {
        "k": top_k,
        "relevance_threshold": relevance_threshold,
        "relevant_rows_total": relevant_total,
        "relevant_rows_in_catalog": relevant_in_catalog,
        "relevant_catalog_coverage": float(relevant_in_catalog / relevant_total)
        if relevant_total
        else 0.0,
        "relevant_users": user_count,
        "users_with_recommendations": users_with_recs,
        "user_coverage": float(users_with_recs / user_count) if user_count else 0.0,
        "precision_at_k": sum(precision_values) / len(precision_values) if precision_values else 0.0,
        "recall_at_k": sum(recall_values) / len(recall_values) if recall_values else 0.0,
        "ndcg_at_k": sum(ndcg_values) / len(ndcg_values) if ndcg_values else 0.0,
    }


def export_model(model: ALSModel, output_dir: Path, params: dict[str, int | float]) -> None:
    factor_dir = output_dir / "model" / "factors"
    factor_dir.mkdir(parents=True, exist_ok=True)
    model.userFactors.toPandas().to_parquet(factor_dir / "user_factors.parquet", index=False)
    model.itemFactors.toPandas().to_parquet(factor_dir / "item_factors.parquet", index=False)
    save_json(
        output_dir / "model" / "metadata.json",
        {
            "algorithm": "Spark MLlib ALS",
            "seed": 42,
            "implicitPrefs": False,
            "nonnegative": True,
            "coldStartStrategy": "drop",
            **params,
        },
    )


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    output_dir = resolve_path(args.output_dir)
    report_dir = resolve_path(args.report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = (
        resolve_path(args.checkpoint_dir)
        if args.checkpoint_dir
        else output_dir / "_spark_checkpoints"
    )
    if args.checkpoint_interval > 0:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
    grid = parse_grid(args.grid)
    spark = build_spark(args)
    # ALS is iterative. Without a checkpoint directory, Spark keeps a growing
    # dependency lineage; larger maxIter values can then overflow the JVM
    # stack while serializing executor tasks on Windows. Passing zero disables
    # the local checkpoint path for Windows setups where Hadoop native I/O is
    # unavailable; the larger JVM thread stack remains enabled above.
    if args.checkpoint_interval > 0:
        spark.sparkContext.setCheckpointDir(str(checkpoint_dir))
    spark.sparkContext.setLogLevel("WARN")
    try:
        # Keep the large full-data frames on disk between actions. Caching all
        # 25M+ rows in the Java heap competes with ALS's block construction.
        train = load_ratings(spark, args.ratings_train).repartition("userId").persist(StorageLevel.DISK_ONLY)
        valid = load_ratings(spark, args.ratings_valid).persist(StorageLevel.DISK_ONLY)
        test = load_ratings(spark, args.ratings_test).persist(StorageLevel.DISK_ONLY)
        train_rows, valid_rows, test_rows = train.count(), valid.count(), test.count()
        tuning_rows: list[dict[str, object]] = []
        best: dict[str, object] | None = None
        for index, params in enumerate(grid, start=1):
            print(f"Tuning {index}/{len(grid)}: {params}")
            als = ALS(
                userCol="userId",
                itemCol="movieId",
                ratingCol="rating",
                coldStartStrategy="drop",
                nonnegative=True,
                implicitPrefs=False,
                rank=int(params["rank"]),
                regParam=float(params["regParam"]),
                maxIter=int(params["maxIter"]),
                numUserBlocks=args.num_user_blocks,
                numItemBlocks=args.num_item_blocks,
                checkpointInterval=max(1, args.checkpoint_interval),
                seed=42,
            )
            model = als.fit(train)
            metrics = rating_metrics(model, valid)
            row = {**params, **metrics}
            tuning_rows.append(row)
            print(f"  validation_rmse={metrics['rmse']:.6f} validation_mae={metrics['mae']:.6f}")
            if best is None or float(metrics["rmse"]) < float(best["rmse"]):
                best = row
        if best is None:
            raise RuntimeError("No ALS configuration was evaluated.")

        tuning_path = report_dir / "als_tuning.csv"
        with tuning_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(tuning_rows[0].keys()))
            writer.writeheader()
            writer.writerows(tuning_rows)

        final_params = {
            "rank": int(best["rank"]),
            "regParam": float(best["regParam"]),
            "maxIter": int(best["maxIter"]),
        }
        fit_frame = train.unionByName(valid).repartition("userId").cache()
        fit_rows = fit_frame.count()
        final_als = ALS(
            userCol="userId",
            itemCol="movieId",
            ratingCol="rating",
            coldStartStrategy="drop",
            nonnegative=True,
            implicitPrefs=False,
            rank=final_params["rank"],
            regParam=final_params["regParam"],
            maxIter=final_params["maxIter"],
            numUserBlocks=args.num_user_blocks,
            numItemBlocks=args.num_item_blocks,
            checkpointInterval=max(1, args.checkpoint_interval),
            seed=42,
        )
        print(f"Fitting final model on {fit_rows:,} rows with {final_params}")
        final_model = final_als.fit(fit_frame)
        test_rating = rating_metrics(final_model, test)
        topk = topk_metrics(
            final_model,
            fit_frame,
            test,
            args.top_k,
            args.candidate_k,
            args.relevance_threshold,
        )
        export_model(final_model, output_dir, final_params)

        movies = spark.read.parquet(str(resolve_path(args.movies))).select("movieId", "title", "genres")
        demo_users = fit_frame.select("userId").distinct().orderBy("userId").limit(args.demo_users)
        demo_recs = make_recommendations(
            final_model,
            demo_users,
            fit_frame.select("userId", "movieId"),
            args.top_k,
            args.candidate_k,
        )
        demo_output = demo_recs.join(movies, "movieId", "left").select(
            "userId", "rank", "movieId", "title", "genres", F.col("score").alias("prediction")
        ).orderBy("userId", "rank")
        recommendation_dir = output_dir / "recommendations"
        recommendation_dir.mkdir(parents=True, exist_ok=True)
        demo_pd = demo_output.toPandas()
        demo_pd.to_parquet(recommendation_dir / "recommendations.parquet", index=False)
        demo_pd.to_csv(recommendation_dir / "recommendations.csv", index=False, encoding="utf-8-sig")

        metrics = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "master": args.master,
            "shuffle_partitions": args.shuffle_partitions,
            "train_rows": train_rows,
            "valid_rows": valid_rows,
            "test_rows": test_rows,
            "fit_rows": fit_rows,
            "selected_params": final_params,
            "num_user_blocks": args.num_user_blocks,
            "num_item_blocks": args.num_item_blocks,
            "driver_memory": args.driver_memory,
            "spark_local_dir": args.spark_local_dir,
            "checkpoint_dir": str(checkpoint_dir) if args.checkpoint_interval > 0 else None,
            "checkpoint_interval": args.checkpoint_interval,
            "selected_validation": best,
            "test_rating_metrics": test_rating,
            "test_topk_metrics": topk,
            "tuning_csv": str(tuning_path),
            "model_dir": str(output_dir / "model"),
            "recommendations_dir": str(recommendation_dir),
            "demo_users": args.demo_users,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        save_json(output_dir / "metrics.json", metrics)
        save_json(report_dir / "test_metrics.json", metrics)
        print(f"OK: tuning table saved to {tuning_path}")
        print(f"test_rmse={test_rating['rmse']:.6f} test_mae={test_rating['mae']:.6f}")
        print(
            "test_" + f"precision@{args.top_k}={topk['precision_at_k']:.6f} "
            + f"recall@{args.top_k}={topk['recall_at_k']:.6f} "
            + f"ndcg@{args.top_k}={topk['ndcg_at_k']:.6f}"
        )
        print(f"OK: final artifacts saved to {output_dir}")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
