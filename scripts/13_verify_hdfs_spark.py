"""Upload MovieLens, run full Spark ETL on HDFS, and verify ALS inference from HDFS.

The trained factors are reused. Outputs get a unique run directory, so no prior
HDFS results or NameNode metadata are overwritten by this verification.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import importlib.util
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hdfs_runtime", ROOT / "scripts/11_hdfs_local.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
ASCII_ROOT = runtime.ascii_root()
LOCAL_HADOOP = ASCII_ROOT / ".hadoop"
os.environ.setdefault("HADOOP_HOME", str(LOCAL_HADOOP))
os.environ["HADOOP_CONF_DIR"] = str(LOCAL_HADOOP / "conf")
os.environ["PATH"] = str(LOCAL_HADOOP / "bin") + os.pathsep + os.environ.get("PATH", "")
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)

from pyspark import StorageLevel
from pyspark.sql import SparkSession, functions as F, types as T


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hdfs", default="hdfs://127.0.0.1:9000/movielens")
    parser.add_argument("--raw-dir", default="ml-32m")
    parser.add_argument("--model-dir", default="models/als_full_iter_20260922_120859")
    parser.add_argument("--user-id", type=int, default=1)
    parser.add_argument("--report-dir", default="reports/tables")
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("hdfs_%Y%m%d_%H%M%S")
    base = args.hdfs.rstrip("/")
    run_path = f"{base}/runs/{run_id}"
    spark = (SparkSession.builder.appName("MovieLens32M-HDFS-ETL-ALS-Demo")
             .master("local[4]").config("spark.driver.memory", "6g")
             .config("spark.driver.host", "127.0.0.1").config("spark.driver.bindAddress", "127.0.0.1")
             .config("spark.sql.shuffle.partitions", "32")
             .config("spark.driver.extraJavaOptions", f"-Djava.library.path={(LOCAL_HADOOP / 'bin').as_posix()}")
             .config("spark.local.dir", str(LOCAL_HADOOP / "spark_tmp"))
             .config("spark.hadoop.dfs.client.use.datanode.hostname", "true").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    jvm = spark._jvm
    fs = jvm.org.apache.hadoop.fs.FileSystem.get(jvm.java.net.URI(base), spark._jsc.hadoopConfiguration())
    hpath = jvm.org.apache.hadoop.fs.Path
    started = time.perf_counter()
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "run_id": run_id,
              "spark_master": spark.sparkContext.master, "spark_version": spark.version,
              "hadoop_version": jvm.org.apache.hadoop.util.VersionInfo.getVersion(),
              "hadoop_native_loaded": bool(jvm.org.apache.hadoop.util.NativeCodeLoader.isNativeCodeLoaded()),
              "hdfs_base": base, "run_path": run_path, "model_retrained": False}

    def upload(local: Path, remote: str) -> None:
        fs.mkdirs(hpath(remote.rsplit("/", 1)[0]))
        if fs.exists(hpath(remote)):
            if fs.getFileStatus(hpath(remote)).getLen() != local.stat().st_size:
                raise RuntimeError(f"HDFS file size differs: {remote}; refusing to overwrite.")
            return
        local_alias = ASCII_ROOT / local.relative_to(ROOT)
        fs.copyFromLocalFile(False, False, hpath(local_alias.as_uri()), hpath(remote))

    try:
        nodes = fs.getDataNodeStats()
        if len(nodes) < 1:
            raise RuntimeError("HDFS has no live DataNode.")
        report["live_datanodes"] = len(nodes)
        report["datanodes"] = [{"name": node.getName(), "capacity_bytes": node.getCapacity()} for node in nodes]
        print(f"HDFS connected: {len(nodes)} live DataNode(s).", flush=True)
        raw_dir = ROOT / args.raw_dir
        for filename in ("ratings.csv", "movies.csv", "tags.csv", "links.csv"):
            upload(raw_dir / filename, f"{base}/raw/{filename}")
            print(f"Uploaded/verified {filename}", flush=True)
        schema = T.StructType([T.StructField("userId", T.IntegerType()), T.StructField("movieId", T.IntegerType()),
                               T.StructField("rating", T.FloatType()), T.StructField("timestamp", T.LongType())])
        ratings = spark.read.schema(schema).option("header", True).option("mode", "FAILFAST").csv(f"{base}/raw/ratings.csv")
        raw_rows = ratings.count()
        valid = ratings.filter(F.col("userId").isNotNull() & (F.col("userId") > 0)
                               & F.col("movieId").isNotNull() & (F.col("movieId") > 0)
                               & F.col("rating").between(0.5, 5.0)
                               & (F.pmod(F.col("rating") * 2, F.lit(1)) == 0)
                               & F.col("timestamp").isNotNull() & (F.col("timestamp") > 0))
        valid = valid.persist(StorageLevel.DISK_ONLY)
        valid_rows = valid.count()
        clean = valid.dropDuplicates(["userId", "movieId", "rating", "timestamp"]).persist(StorageLevel.DISK_ONLY)
        clean_rows = clean.count()
        if raw_rows != 32_000_204 or clean_rows != 32_000_204:
            raise RuntimeError(f"Unexpected MovieLens 32M row counts: raw={raw_rows}, clean={clean_rows}.")
        parquet_path = f"{run_path}/processed/ratings"
        clean.repartition(32, "userId").sortWithinPartitions("userId", "timestamp").write.parquet(parquet_path)
        other_schemas = {
            "movies": (T.StructType([T.StructField("movieId", T.IntegerType()), T.StructField("title", T.StringType()), T.StructField("genres", T.StringType())]), 87_585),
            "tags": (T.StructType([T.StructField("userId", T.IntegerType()), T.StructField("movieId", T.IntegerType()), T.StructField("tag", T.StringType()), T.StructField("timestamp", T.LongType())]), 2_000_072),
            "links": (T.StructType([T.StructField("movieId", T.IntegerType()), T.StructField("imdbId", T.StringType()), T.StructField("tmdbId", T.LongType())]), 87_585),
        }
        report["other_tables"] = {}
        for filename, (other_schema, expected_rows) in other_schemas.items():
            # IMDb IDs retain leading zeros; quoted tags/titles can span lines.
            frame = (spark.read.schema(other_schema).option("header", True).option("escape", '"')
                     .option("multiLine", True).option("mode", "FAILFAST").csv(f"{base}/raw/{filename}.csv"))
            other_path = f"{run_path}/processed/{filename}"
            frame.write.parquet(other_path)
            actual_rows = spark.read.parquet(other_path).count()
            if actual_rows != expected_rows:
                raise RuntimeError(f"Unexpected {filename} rows: {actual_rows} != {expected_rows}")
            report["other_tables"][filename] = {"rows": actual_rows, "parquet_path": other_path}
        hdfs_ratings = spark.read.parquet(parquet_path)
        readback_rows = hdfs_ratings.count()
        if readback_rows != clean_rows:
            raise RuntimeError("HDFS Parquet readback count does not match ETL output.")
        report["etl"] = {"raw_rows": raw_rows, "valid_rows": valid_rows, "clean_rows": clean_rows,
                         "invalid_rows": raw_rows - valid_rows, "duplicate_rows": valid_rows - clean_rows,
                         "parquet_rows_readback": readback_rows, "parquet_path": parquet_path,
                         "input_file_example": hdfs_ratings.inputFiles()[0]}
        spark.sparkContext.setCheckpointDir(f"{run_path}/checkpoints")
        summary = hdfs_ratings.groupBy("rating").count().orderBy("rating").checkpoint(eager=True)
        summary.write.json(f"{run_path}/results/rating_distribution")
        report["rating_distribution"] = [row.asDict() for row in summary.collect()]
        print(f"Spark HDFS ETL/readback passed: {readback_rows:,} rows.", flush=True)
        clean.unpersist()
        valid.unpersist()

        model_dir = ROOT / args.model_dir
        model_remote = f"{base}/models/{model_dir.name}"
        for local in (model_dir / "model").rglob("*"):
            if local.is_file():
                upload(local, f"{model_remote}/model/{local.relative_to(model_dir / 'model').as_posix()}")
        upload(model_dir / "metrics.json", f"{model_remote}/metrics.json")
        upload(ROOT / "artifacts/catalog/movie_catalog.parquet", f"{run_path}/catalog/movie_catalog.parquet")
        users = spark.read.parquet(f"{model_remote}/model/factors/user_factors.parquet").filter(F.col("id") == args.user_id).select(F.col("features").alias("user_features"))
        if users.count() != 1:
            raise ValueError("Demo User ID has no model factor.")
        items = spark.read.parquet(f"{model_remote}/model/factors/item_factors.parquet").select(F.col("id").alias("movieId"), F.col("features").alias("item_features"))
        catalog = spark.read.parquet(f"{run_path}/catalog/movie_catalog.parquet").filter("rating_count >= 100").select("movieId", "title", "rating_count")
        seen = hdfs_ratings.filter(F.col("userId") == args.user_id).select("movieId").distinct()
        candidates = items.join(catalog, "movieId").join(seen, "movieId", "left_anti").crossJoin(users)
        scores = F.aggregate(F.zip_with("item_features", "user_features", lambda x, y: x.cast("double") * y.cast("double")), F.lit(0.0), lambda acc, x: acc + x)
        recommendations = candidates.withColumn("prediction", scores).select("movieId", "title", "prediction", "rating_count").orderBy(F.desc("prediction"), F.asc("movieId")).limit(10)
        rows = [row.asDict() for row in recommendations.collect()]
        recommendations.write.parquet(f"{run_path}/results/als_user_{args.user_id}")
        report["als_demo"] = {"user_id": args.user_id, "source_model": args.model_dir,
                              "model_path": model_remote, "seen_movies_excluded": seen.count(),
                              "candidate_min_rating_count": 100, "recommendations": rows}
        report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        report["success"] = True
        report_dir = ROOT / args.report_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "hdfs_spark_verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"success": True, "ratings": readback_rows, "live_datanodes": len(nodes),
                          "als_user": args.user_id, "top_k": len(rows), "seconds": report["elapsed_seconds"]}, indent=2), flush=True)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
