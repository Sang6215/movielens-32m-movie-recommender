from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
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
    hadoop_bin = local_hadoop / "bin"
    os.environ["PATH"] = f"{hadoop_bin}{os.pathsep}{os.environ.get('PATH', '')}"

os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession, functions as F, types as T

sys.path.append(str(project_root / "src"))
from recommender.config import resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Big Data benchmarks: CSV vs Parquet and Spark local[1]/local[2]/local[4] scaling."
    )
    parser.add_argument("--csv-dir", default="ml-32m")
    parser.add_argument("--parquet-dir", default="data/processed/parquet")
    parser.add_argument("--sample-train", default="data/interim/train.parquet")
    parser.add_argument("--sample-valid", default="data/interim/valid.parquet")
    parser.add_argument("--report-dir", default="reports/tables")
    parser.add_argument("--format-runs", type=int, default=3)
    return parser.parse_args()


def build_spark(master: str, shuffle_partitions: int = 32, driver_memory: str = "8g") -> SparkSession:
    return (
        SparkSession.builder.appName(f"movielens32m-benchmark-{master}")
        .master(master)
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.memory", driver_memory)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.ansi.enabled", "false")
        .getOrCreate()
    )


def file_size_mb(path: Path) -> float:
    if path.is_file():
        return path.stat().st_size / (1024 * 1024)
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def benchmark_csv_vs_parquet(
    csv_dir: Path, parquet_dir: Path, runs: int
) -> tuple[list[dict[str, object]], dict[str, object]]:
    storage_rows: list[dict[str, object]] = []
    for name in ("ratings", "movies", "tags", "links"):
        csv_path = csv_dir / f"{name}.csv"
        pq_path = parquet_dir / f"{name}.parquet"
        csv_mb = round(file_size_mb(csv_path), 2)
        pq_mb = round(file_size_mb(pq_path), 2)
        ratio = round((1.0 - pq_mb / csv_mb) * 100.0, 2) if csv_mb > 0 else 0.0
        storage_rows.append(
            {
                "dataset": name,
                "csv_size_mb": csv_mb,
                "parquet_size_mb": pq_mb,
                "space_saving_pct": ratio,
            }
        )

    spark = build_spark("local[4]", shuffle_partitions=64)
    spark.sparkContext.setLogLevel("WARN")
    try:
        schema = T.StructType(
            [
                T.StructField("userId", T.IntegerType(), False),
                T.StructField("movieId", T.IntegerType(), False),
                T.StructField("rating", T.FloatType(), False),
                T.StructField("timestamp", T.LongType(), False),
            ]
        )
        csv_ratings_path = str(csv_dir / "ratings.csv")
        pq_ratings_path = str(parquet_dir / "ratings.parquet")

        csv_times: list[float] = []
        pq_times: list[float] = []

        for r in range(1, runs + 1):
            t0 = time.perf_counter()
            df_csv = spark.read.csv(csv_ratings_path, header=True, schema=schema)
            agg_csv = (
                df_csv.groupBy("movieId")
                .agg(F.count("*").alias("cnt"), F.avg("rating").alias("avg_r"))
                .agg(F.sum("cnt"), F.avg("avg_r"))
                .first()
            )
            elapsed_csv = round(time.perf_counter() - t0, 3)
            csv_times.append(elapsed_csv)
            print(f"  CSV aggregation run {r}/{runs}: {elapsed_csv:.3f}s (rows={agg_csv[0]:,})")

            t1 = time.perf_counter()
            df_pq = spark.read.parquet(pq_ratings_path).select("movieId", "rating")
            agg_pq = (
                df_pq.groupBy("movieId")
                .agg(F.count("*").alias("cnt"), F.avg("rating").alias("avg_r"))
                .agg(F.sum("cnt"), F.avg("avg_r"))
                .first()
            )
            elapsed_pq = round(time.perf_counter() - t1, 3)
            pq_times.append(elapsed_pq)
            print(f"  Parquet aggregation run {r}/{runs}: {elapsed_pq:.3f}s (rows={agg_pq[0]:,})")

        csv_med = round(statistics.median(csv_times), 3)
        pq_med = round(statistics.median(pq_times), 3)
        speedup = round(csv_med / pq_med, 2) if pq_med > 0 else 0.0

        query_comparison = {
            "query": "Read 32M ratings + groupBy(movieId).agg(count, avg)",
            "master": "local[4]",
            "runs": runs,
            "csv_times_sec": csv_times,
            "parquet_times_sec": pq_times,
            "csv_median_sec": csv_med,
            "parquet_median_sec": pq_med,
            "parquet_speedup_x": speedup,
        }
        return storage_rows, query_comparison
    finally:
        spark.stop()


def benchmark_thread_scaling(train_path: Path, valid_path: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    base_total: float | None = None

    for master, threads in (("local[1]", 1), ("local[2]", 2), ("local[4]", 4)):
        print(f"Running thread scaling benchmark with {master}...")
        spark = build_spark(master, shuffle_partitions=32)
        spark.sparkContext.setLogLevel("WARN")
        try:
            t_start = time.perf_counter()
            train = (
                spark.read.parquet(str(train_path))
                .select(
                    F.col("userId").cast("int"),
                    F.col("movieId").cast("int"),
                    F.col("rating").cast("float"),
                )
                .repartition(32, "userId")
                .cache()
            )
            valid = (
                spark.read.parquet(str(valid_path))
                .select(
                    F.col("userId").cast("int"),
                    F.col("movieId").cast("int"),
                    F.col("rating").cast("float"),
                )
                .cache()
            )
            train_rows = train.count()
            valid_rows = valid.count()
            load_sec = round(time.perf_counter() - t_start, 3)

            t_fit = time.perf_counter()
            als = ALS(
                userCol="userId",
                itemCol="movieId",
                ratingCol="rating",
                coldStartStrategy="drop",
                nonnegative=True,
                implicitPrefs=False,
                rank=16,
                regParam=0.08,
                maxIter=5,
                numUserBlocks=16,
                numItemBlocks=16,
                seed=42,
            )
            model = als.fit(train)
            preds = model.transform(valid)
            rmse = RegressionEvaluator(
                metricName="rmse", labelCol="rating", predictionCol="prediction"
            ).evaluate(preds)
            fit_eval_sec = round(time.perf_counter() - t_fit, 3)
            total_sec = round(load_sec + fit_eval_sec, 3)

            if base_total is None:
                base_total = total_sec
            speedup = round(base_total / total_sec, 2) if total_sec > 0 else 1.0

            row = {
                "master": master,
                "threads": threads,
                "train_rows": train_rows,
                "valid_rows": valid_rows,
                "load_and_cache_sec": load_sec,
                "als_fit_and_eval_sec": fit_eval_sec,
                "total_sec": total_sec,
                "rmse": round(float(rmse), 6),
                "speedup_vs_1_thread": speedup,
            }
            results.append(row)
            print(
                f"  {master}: load={load_sec:.2f}s, fit+eval={fit_eval_sec:.2f}s, "
                f"total={total_sec:.2f}s, speedup={speedup:.2f}x"
            )
            train.unpersist()
            valid.unpersist()
        finally:
            spark.stop()

    return results


def main() -> int:
    args = parse_args()
    csv_dir = resolve_path(args.csv_dir)
    parquet_dir = resolve_path(args.parquet_dir)
    sample_train = resolve_path(args.sample_train)
    sample_valid = resolve_path(args.sample_valid)
    report_dir = resolve_path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    print("=== 1. Benchmarking CSV vs Parquet ===")
    storage_rows, query_comparison = benchmark_csv_vs_parquet(
        csv_dir, parquet_dir, args.format_runs
    )

    print("\n=== 2. Benchmarking Spark Thread Scaling (local[1], local[2], local[4]) ===")
    scaling_rows = benchmark_thread_scaling(sample_train, sample_valid)

    # Save CSV
    csv_path = report_dir / "bigdata_benchmarks.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scaling_rows[0].keys()))
        writer.writeheader()
        writer.writerows(scaling_rows)

    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "storage_comparison": storage_rows,
        "format_query_benchmark": query_comparison,
        "spark_thread_scaling": scaling_rows,
    }
    json_path = report_dir / "bigdata_benchmarks.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write Markdown summary
    md_lines = [
        "# Kết quả Thực nghiệm Hiệu năng Big Data (MovieLens 32M)",
        "",
        "## 1. So sánh dung lượng lưu trữ CSV và Parquet",
        "",
        "| Bảng dữ liệu | CSV gốc (MB) | Parquet sau ETL (MB) | Tiết kiệm dung lượng (%) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for s in storage_rows:
        md_lines.append(
            f"| `{s['dataset']}` | {s['csv_size_mb']:.2f} | {s['parquet_size_mb']:.2f} | {s['space_saving_pct']:.2f}% |"
        )
    md_lines.extend(
        [
            "",
            "## 2. So sánh thời gian truy vấn tổng hợp 32 triệu dòng (CSV vs Parquet)",
            "",
            f"- Truy vấn: `{query_comparison['query']}` trên `{query_comparison['master']}` ({query_comparison['runs']} lần chạy).",
            f"- Thời gian đọc & tổng hợp CSV: các lần chạy `{query_comparison['csv_times_sec']}` giây -> **Trung vị: {query_comparison['csv_median_sec']:.3f} giây**.",
            f"- Thời gian đọc & tổng hợp Parquet: các lần chạy `{query_comparison['parquet_times_sec']}` giây -> **Trung vị: {query_comparison['parquet_median_sec']:.3f} giây**.",
            f"- **Tốc độ tăng tốc (Speedup) của Parquet so với CSV:** **{query_comparison['parquet_speedup_x']:.2f} lần** (nhờ đọc cột chọn lọc `movieId, rating` và nén cột nhị phân).",
            "",
            "## 3. Thực nghiệm tăng số luồng xử lý Spark (`local[1]` vs `local[2]` vs `local[4]`)",
            "",
            "Đo trên tập phát triển (`2,519,826` dòng train + `314,807` dòng validation) với cấu hình ALS `rank=16, regParam=0.08, maxIter=5`:",
            "",
            "| Cấu hình Spark | Số luồng | Nạp & Cache (giây) | Huấn luyện ALS & Đánh giá (giây) | Tổng thời gian (giây) | RMSE Validation | Tăng tốc (Speedup) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for r in scaling_rows:
        md_lines.append(
            f"| `{r['master']}` | {r['threads']} | {r['load_and_cache_sec']:.3f} | {r['als_fit_and_eval_sec']:.3f} | {r['total_sec']:.3f} | {r['rmse']:.6f} | {r['speedup_vs_1_thread']:.2f}x |"
        )

    md_path = report_dir / "bigdata_benchmarks.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"\nOK: Saved {csv_path}, {json_path}, and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
