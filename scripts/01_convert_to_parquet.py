from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.csv as pcsv
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from recommender.config import resolve_path
from recommender.local_io import ensure_dir


SCHEMAS: dict[str, pa.Schema] = {
    "ratings.csv": pa.schema(
        [
            ("userId", pa.int32()),
            ("movieId", pa.int32()),
            ("rating", pa.float32()),
            ("timestamp", pa.int64()),
        ]
    ),
    "movies.csv": pa.schema(
        [
            ("movieId", pa.int32()),
            ("title", pa.string()),
            ("genres", pa.string()),
        ]
    ),
    "tags.csv": pa.schema(
        [
            ("userId", pa.int32()),
            ("movieId", pa.int32()),
            ("tag", pa.string()),
            ("timestamp", pa.int64()),
        ]
    ),
    "links.csv": pa.schema(
        [
            ("movieId", pa.int32()),
            ("imdbId", pa.string()),
            ("tmdbId", pa.string()),
        ]
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert MovieLens 32M CSV files to Parquet.")
    parser.add_argument("--data-dir", default="ml-32m", help="Folder containing raw CSV files.")
    parser.add_argument("--output-dir", default="data/processed/parquet", help="Parquet output folder.")
    parser.add_argument("--compression", default="snappy", help="Parquet compression codec.")
    return parser.parse_args()


def convert_one(csv_path: Path, output_path: Path, schema: pa.Schema, compression: str) -> None:
    read_options = pcsv.ReadOptions(block_size=64 * 1024 * 1024)
    convert_options = pcsv.ConvertOptions(column_types=schema)

    reader = pcsv.open_csv(csv_path, read_options=read_options, convert_options=convert_options)
    writer: pq.ParquetWriter | None = None
    rows = 0

    try:
        for batch in reader:
            table = pa.Table.from_batches([batch])
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression=compression)
            writer.write_table(table)
            rows += batch.num_rows
    finally:
        if writer is not None:
            writer.close()

    print(f"{csv_path.name} -> {output_path} ({rows:,} rows)")


def main() -> int:
    args = parse_args()
    data_dir = resolve_path(args.data_dir)
    output_dir = ensure_dir(resolve_path(args.output_dir))

    for filename, schema in SCHEMAS.items():
        csv_path = data_dir / filename
        output_path = output_dir / filename.replace(".csv", ".parquet")
        if not csv_path.exists():
            raise FileNotFoundError(csv_path)
        convert_one(csv_path, output_path, schema, args.compression)

    print(f"\nOK: Parquet files written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
