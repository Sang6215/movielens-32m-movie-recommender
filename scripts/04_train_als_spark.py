from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# The small Hadoop helper is kept inside the project so Spark can write local
# model/Parquet output on Windows without requiring a system-wide Hadoop setup.
_project_root = Path(__file__).resolve().parents[1]
_local_hadoop = _project_root / ".hadoop"
if (_local_hadoop / "bin" / "winutils.exe").exists():
    os.environ.setdefault("HADOOP_HOME", str(_local_hadoop))
    os.environ.setdefault("hadoop.home.dir", str(_local_hadoop))

# Keep the Python interpreter used by Spark workers identical to the one used
# to launch this script. This is useful on Windows, where several Python
# installations can otherwise be discovered by the Spark launcher.
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql import DataFrame, SparkSession, functions as F

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from recommender.config import resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train Spark MLlib ALS, compare baselines and export demo recommendations."
    )
    parser.add_argument("--ratings-train", required=True, help="Train ratings Parquet path.")
    parser.add_argument("--ratings-valid", required=True, help="Validation ratings Parquet path.")
    parser.add_argument("--movies", default="data/processed/parquet/movies.parquet")
    parser.add_argument("--output-dir", default="models/als_dev", help="Model and metrics output folder.")
    parser.add_argument("--rank", type=int, default=32)
    parser.add_argument("--reg-param", type=float, default=0.08)
    parser.add_argument("--max-iter", type=int, default=8)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--demo-users", type=int, default=200)
    parser.add_argument("--master", default="local[4]", help="Spark master, e.g. local[4].")
    parser.add_argument("--shuffle-partitions", type=int, default=64)
    return parser.parse_args()


def regression_metrics(frame: DataFrame) -> dict[str, float | int]:
    """Evaluate rating predictions and return values that are JSON serializable."""
    rows = frame.count()
    if rows == 0:
        return {"rows": 0, "rmse": None, "mae": None}
    rmse = RegressionEvaluator(
        metricName="rmse", labelCol="rating", predictionCol="prediction"
    ).evaluate(frame)
    mae = RegressionEvaluator(
        metricName="mae", labelCol="rating", predictionCol="prediction"
    ).evaluate(frame)
    return {"rows": rows, "rmse": float(rmse), "mae": float(mae)}


def save_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_spark(args: argparse.Namespace) -> SparkSession:
    return (
        SparkSession.builder.appName("movielens32m-als")
        .master(args.master)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.shuffle.partitions", str(args.shuffle_partitions))
        .config("spark.sql.ansi.enabled", "false")
        .getOrCreate()
    )


def main() -> int:
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    model_dir = output_dir / "model"
    factor_dir = model_dir / "factors"
    recommendation_dir = output_dir / "recommendations"
    metrics_path = output_dir / "metrics.json"
    movies_path = resolve_path(args.movies)

    started = time.perf_counter()
    spark = build_spark(args)
    spark.sparkContext.setLogLevel("WARN")
    try:
        train = spark.read.parquet(str(resolve_path(args.ratings_train))).select(
            "userId", "movieId", "rating"
        )
        valid = spark.read.parquet(str(resolve_path(args.ratings_valid))).select(
            "userId", "movieId", "rating"
        )
        train = train.select(
            F.col("userId").cast("int"),
            F.col("movieId").cast("int"),
            F.col("rating").cast("float"),
        ).repartition("userId").cache()
        valid = valid.select(
            F.col("userId").cast("int"),
            F.col("movieId").cast("int"),
            F.col("rating").cast("float"),
        ).cache()
        train_rows = train.count()
        valid_rows = valid.count()
        train_users = train.select("userId").distinct().count()
        train_movies = train.select("movieId").distinct().count()

        global_mean = float(train.agg(F.avg("rating")).first()[0])
        global_predictions = valid.withColumn("prediction", F.lit(global_mean))
        global_metrics = regression_metrics(global_predictions)

        item_means = train.groupBy("movieId").agg(F.avg("rating").alias("item_mean"))
        item_predictions = (
            valid.join(item_means, on="movieId", how="left")
            .withColumn("prediction", F.coalesce(F.col("item_mean"), F.lit(global_mean)))
            .drop("item_mean")
        )
        item_metrics = regression_metrics(item_predictions)

        popularity = (
            train.groupBy("movieId")
            .agg(
                F.count("*").alias("rating_count"),
                F.avg("rating").alias("mean_rating"),
            )
            .orderBy(F.desc("rating_count"), F.desc("mean_rating"), F.asc("movieId"))
        )
        popularity_rows = [row.asDict() for row in popularity.limit(args.top_k).collect()]
        baseline_payload = {
            "global_mean": global_mean,
            "global_mean_metrics": global_metrics,
            "item_mean_metrics": item_metrics,
            "popularity_top_k": popularity_rows,
        }
        save_json(output_dir / "baseline_metrics.json", baseline_payload)

        als = ALS(
            userCol="userId",
            itemCol="movieId",
            ratingCol="rating",
            coldStartStrategy="drop",
            nonnegative=True,
            implicitPrefs=False,
            rank=args.rank,
            regParam=args.reg_param,
            maxIter=args.max_iter,
            seed=42,
        )
        print(
            f"Fitting ALS: train_rows={train_rows:,}, valid_rows={valid_rows:,}, "
            f"users={train_users:,}, movies={train_movies:,}, "
            f"rank={args.rank}, regParam={args.reg_param}, maxIter={args.max_iter}"
        )
        model = als.fit(train)
        predictions = model.transform(valid).cache()
        als_metrics = regression_metrics(predictions)
        # Spark's JVM writer requires the Hadoop Windows native library. To
        # keep this project portable, persist the fitted factor tables through
        # pandas/Arrow instead of Spark's Hadoop commit protocol. They are the
        # actual ALS model parameters and are small compared with the ratings.
        factor_dir.mkdir(parents=True, exist_ok=True)
        model.userFactors.toPandas().to_parquet(factor_dir / "user_factors.parquet", index=False)
        model.itemFactors.toPandas().to_parquet(factor_dir / "item_factors.parquet", index=False)
        save_json(
            model_dir / "metadata.json",
            {
                "algorithm": "Spark MLlib ALS",
                "rank": args.rank,
                "regParam": args.reg_param,
                "maxIter": args.max_iter,
                "seed": 42,
                "implicitPrefs": False,
                "nonnegative": True,
                "coldStartStrategy": "drop",
            },
        )

        # Export recommendations for a bounded set of users. The UI reads this
        # small artifact, so it never has to fit Spark models in a web request.
        demo_users = train.select("userId").distinct().orderBy("userId").limit(args.demo_users)
        recommendations = model.recommendForUserSubset(demo_users, args.top_k)
        flat = (
            recommendations.select("userId", F.posexplode("recommendations").alias("rank0", "rec"))
            .select(
                "userId",
                (F.col("rank0") + F.lit(1)).alias("rank"),
                F.col("rec.movieId").cast("int").alias("movieId"),
                F.col("rec.rating").cast("double").alias("prediction"),
            )
        )
        movies = spark.read.parquet(str(movies_path)).select("movieId", "title", "genres")
        demo_output = flat.join(movies, on="movieId", how="left").select(
            "userId", "rank", "movieId", "title", "genres", "prediction"
        )
        recommendation_dir.mkdir(parents=True, exist_ok=True)
        demo_output_pd = demo_output.orderBy("userId", "rank").toPandas()
        demo_output_pd.to_parquet(recommendation_dir / "recommendations.parquet", index=False)
        demo_output_pd.to_csv(recommendation_dir / "recommendations.csv", index=False, encoding="utf-8-sig")
        recommendation_rows = len(demo_output_pd)

        metrics = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "master": args.master,
            "shuffle_partitions": args.shuffle_partitions,
            "train_path": str(resolve_path(args.ratings_train)),
            "valid_path": str(resolve_path(args.ratings_valid)),
            "train_rows": train_rows,
            "valid_rows": valid_rows,
            "train_users": train_users,
            "train_movies": train_movies,
            "global_mean": global_mean,
            "baseline_global_mean": global_metrics,
            "baseline_item_mean": item_metrics,
            "als": {
                "rank": args.rank,
                "regParam": args.reg_param,
                "maxIter": args.max_iter,
                "rmse": als_metrics["rmse"],
                "mae": als_metrics["mae"],
                "evaluated_rows": als_metrics["rows"],
                "coverage": (
                    float(als_metrics["rows"]) / valid_rows if valid_rows else 0.0
                ),
            },
            "model_dir": str(model_dir),
            "recommendations_dir": str(recommendation_dir),
            "recommendation_rows": recommendation_rows,
            "demo_users": args.demo_users,
            "top_k": args.top_k,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        save_json(metrics_path, metrics)
        print(f"validation_rmse={als_metrics['rmse']:.6f}")
        print(f"validation_mae={als_metrics['mae']:.6f}")
        print(f"validation_coverage={metrics['als']['coverage']:.4f}")
        print(f"OK: ALS model saved to {model_dir}")
        print(f"OK: demo recommendations saved to {recommendation_dir} ({recommendation_rows:,} rows)")
        print(f"OK: metrics saved to {metrics_path}")
        return 0
    finally:
        spark.stop()


if __name__ == "__main__":
    raise SystemExit(main())
