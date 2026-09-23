from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Windows Hadoop configuration for local PySpark execution
_project_root = Path(__file__).resolve().parents[1]
_local_hadoop = _project_root / ".hadoop"
if (_local_hadoop / "bin" / "winutils.exe").exists():
    os.environ.setdefault("HADOOP_HOME", str(_local_hadoop))
    os.environ.setdefault("hadoop.home.dir", str(_local_hadoop))

os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

from pyspark.sql import SparkSession, functions as F

sys.path.append(str(_project_root / "src"))
from recommender.config import resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate MovieLens ratings and build movie catalog with weighted ratings."
    )
    parser.add_argument(
        "--ratings-train",
        default="data/full_interim/train.parquet",
        help="Train ratings Parquet path.",
    )
    parser.add_argument(
        "--ratings-valid",
        default="data/full_interim/valid.parquet",
        help="Validation ratings Parquet path.",
    )
    parser.add_argument(
        "--movies",
        default="data/processed/parquet/movies.parquet",
        help="Processed movies Parquet path.",
    )
    parser.add_argument(
        "--links",
        default="data/processed/parquet/links.parquet",
        help="Processed links Parquet path.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/catalog",
        help="Destination directory for catalog and manifest.",
    )
    parser.add_argument(
        "--m",
        type=float,
        default=100.0,
        help="Regularization constant m for weighted score (default 100).",
    )
    parser.add_argument("--master", default="local[4]", help="Spark master, e.g. local[4].")
    parser.add_argument("--shuffle-partitions", type=int, default=64)
    return parser.parse_args()


def build_spark(args: argparse.Namespace) -> SparkSession:
    return (
        SparkSession.builder.appName("movielens32m-build-catalog")
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
    output_dir.mkdir(parents=True, exist_ok=True)

    ratings_train_path = resolve_path(args.ratings_train)
    ratings_valid_path = resolve_path(args.ratings_valid)
    movies_path = resolve_path(args.movies)
    links_path = resolve_path(args.links)

    print(f"Loading ratings from:")
    print(f"  Train: {ratings_train_path}")
    print(f"  Valid: {ratings_valid_path}")
    print(f"Loading metadata from:")
    print(f"  Movies: {movies_path}")
    print(f"  Links:  {links_path}")

    start_time = time.perf_counter()
    spark = build_spark(args)

    # 1. Read ratings from train and valid
    df_train = spark.read.parquet(str(ratings_train_path)).select("movieId", "rating")
    df_valid = spark.read.parquet(str(ratings_valid_path)).select("movieId", "rating")
    ratings = df_train.unionByName(df_valid)

    # 2. Compute global statistics: total ratings count and global average rating C
    global_stats = ratings.select(
        F.count("rating").alias("total_ratings"),
        F.avg("rating").alias("global_mean"),
    ).first()
    total_ratings = int(global_stats["total_ratings"])
    global_mean_c = float(global_stats["global_mean"])
    print(f"Total ratings combined: {total_ratings:,}")
    print(f"Global average rating C: {global_mean_c:.4f}")

    # 3. Group by movieId to get v (rating_count) and R (avg_rating)
    m = float(args.m)
    movie_stats = ratings.groupBy("movieId").agg(
        F.count("rating").alias("rating_count"),
        F.avg("rating").alias("avg_rating"),
    )

    # Calculate weighted_score = (v * R + m * C) / (v + m)
    movie_stats = movie_stats.withColumn(
        "weighted_score",
        (F.col("rating_count") * F.col("avg_rating") + F.lit(m * global_mean_c))
        / (F.col("rating_count") + F.lit(m)),
    )

    # 4. Read and process movies metadata
    df_movies = spark.read.parquet(str(movies_path))
    # Extract year from title, e.g. "Toy Story (1995)" -> 1995
    df_movies = df_movies.withColumn(
        "_year_str",
        F.regexp_extract(F.col("title"), r"\((\d{4})\)[^\d]*$", 1),
    ).withColumn(
        "year",
        F.when(F.col("_year_str") != "", F.col("_year_str").cast("int")).otherwise(F.lit(None)),
    ).drop("_year_str")

    # Split genres string by "|"
    df_movies = df_movies.withColumn("genres", F.split(F.col("genres"), r"\|"))

    # 5. Read and process links metadata
    df_links = spark.read.parquet(str(links_path))
    # Preserve the exact IMDb ID for a verified fallback when an old TMDB movie link is gone.
    df_links = df_links.withColumn(
        "tmdbId",
        F.when(F.col("tmdbId").rlike(r"^\d+$"), F.col("tmdbId").cast("long")).otherwise(F.lit(None)),
    ).withColumn(
        "imdbId",
        F.when(F.col("imdbId").rlike(r"^\d+$"), F.col("imdbId")).otherwise(F.lit(None)),
    ).select("movieId", "tmdbId", "imdbId")

    # 6. Join movies + links + rating stats
    catalog_df = df_movies.join(df_links, on="movieId", how="left")
    catalog_df = catalog_df.join(movie_stats, on="movieId", how="left")

    # Fill rating_count nulls with 0
    catalog_df = catalog_df.withColumn(
        "rating_count",
        F.coalesce(F.col("rating_count"), F.lit(0)).cast("int"),
    )

    # Order catalog deterministically
    catalog_df = catalog_df.select(
        "movieId",
        "title",
        "year",
        "genres",
        "avg_rating",
        "rating_count",
        "weighted_score",
        "tmdbId",
        "imdbId",
    ).orderBy("movieId")

    print("Collecting catalog to local pandas DataFrame...")
    pdf_catalog = catalog_df.toPandas()

    total_movies = len(pdf_catalog)
    movies_with_ratings = int((pdf_catalog["rating_count"] > 0).sum())
    print(f"Catalog total movies: {total_movies:,}")
    print(f"Movies with ratings: {movies_with_ratings:,}")

    # Ensure clean nullable integer types for pandas
    pdf_catalog["movieId"] = pdf_catalog["movieId"].astype("int32")
    pdf_catalog["year"] = pdf_catalog["year"].astype("Int32")
    pdf_catalog["rating_count"] = pdf_catalog["rating_count"].astype("int32")
    pdf_catalog["tmdbId"] = pdf_catalog["tmdbId"].astype("Int64")
    pdf_catalog["imdbId"] = pdf_catalog["imdbId"].astype("string")
    # Convert numpy ndarrays in genres to clean python lists
    pdf_catalog["genres"] = pdf_catalog["genres"].apply(
        lambda g: list(g) if isinstance(g, (list, pd.Series, tuple)) or hasattr(g, "__iter__") else []
    )

    # Save single parquet file
    catalog_file = output_dir / "movie_catalog.parquet"
    pdf_catalog.to_parquet(catalog_file, index=False)
    print(f"OK: Saved movie catalog to {catalog_file} ({catalog_file.stat().st_size / 1024 / 1024:.2f} MB)")

    # Save manifest.json
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ratings_sources": [
            str(ratings_train_path.relative_to(_project_root)),
            str(ratings_valid_path.relative_to(_project_root)),
        ],
        "movies_source": str(movies_path.relative_to(_project_root)),
        "links_source": str(links_path.relative_to(_project_root)),
        "total_ratings": total_ratings,
        "global_avg_rating_C": round(global_mean_c, 6),
        "m_regularization": m,
        "total_movies": total_movies,
        "movies_with_ratings": movies_with_ratings,
        "catalog_file": catalog_file.name,
        "columns": list(pdf_catalog.columns),
    }
    manifest_file = output_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: Saved manifest to {manifest_file}")

    spark.stop()
    elapsed = time.perf_counter() - start_time
    print(f"Catalog build completed in {elapsed:.2f} seconds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
