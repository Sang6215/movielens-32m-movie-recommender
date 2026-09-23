from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from recommender.config import resolve_path
from recommender.local_io import ensure_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a dev sample and chronological train/valid/test splits.")
    parser.add_argument("--parquet-dir", default="data/processed/parquet", help="Parquet input folder.")
    parser.add_argument("--output-dir", default="data/interim", help="Output folder.")
    parser.add_argument("--user-mod", type=int, default=10, help="Keep users where userId %% user_mod == 0.")
    parser.add_argument("--valid-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    return parser.parse_args()


def write_dev_sample(ratings_path: Path, output_path: Path, user_mod: int) -> int:
    dataset = ds.dataset(ratings_path, format="parquet")
    scanner = dataset.scanner(columns=["userId", "movieId", "rating", "timestamp"], batch_size=1_000_000)
    writer: pq.ParquetWriter | None = None
    kept_rows = 0

    try:
        for batch in scanner.to_batches():
            frame = batch.to_pandas()
            sample = frame[frame["userId"] % user_mod == 0]
            if sample.empty:
                continue
            table = pa.Table.from_pandas(sample, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output_path, table.schema, compression="snappy")
            writer.write_table(table)
            kept_rows += len(sample)
    finally:
        if writer is not None:
            writer.close()

    return kept_rows


def split_chronologically(sample_path: Path, output_dir: Path, valid_ratio: float, test_ratio: float) -> dict[str, int]:
    ratings = pd.read_parquet(sample_path)
    ratings = ratings.sort_values(["userId", "timestamp", "movieId"]).reset_index(drop=True)

    group_sizes = ratings.groupby("userId")["movieId"].transform("size")
    group_rank = ratings.groupby("userId").cumcount()
    train_cutoff = (group_sizes * (1 - valid_ratio - test_ratio)).astype(int)
    valid_cutoff = (group_sizes * (1 - test_ratio)).astype(int)

    train = ratings[group_rank < train_cutoff]
    valid = ratings[(group_rank >= train_cutoff) & (group_rank < valid_cutoff)]
    test = ratings[group_rank >= valid_cutoff]

    train.to_parquet(output_dir / "train.parquet", index=False)
    valid.to_parquet(output_dir / "valid.parquet", index=False)
    test.to_parquet(output_dir / "test.parquet", index=False)

    return {"train": len(train), "valid": len(valid), "test": len(test), "users": ratings["userId"].nunique()}


def main() -> int:
    args = parse_args()
    parquet_dir = resolve_path(args.parquet_dir)
    output_dir = ensure_dir(resolve_path(args.output_dir))
    sample_path = output_dir / "ratings_dev_sample.parquet"

    kept_rows = write_dev_sample(parquet_dir / "ratings.parquet", sample_path, args.user_mod)
    counts = split_chronologically(sample_path, output_dir, args.valid_ratio, args.test_ratio)

    summary_path = output_dir / "split_summary.md"
    summary_path.write_text(
        "\n".join(
            [
                "# Split Summary",
                "",
                f"- User filter: `userId % {args.user_mod} == 0`",
                f"- Sample ratings: {kept_rows:,}",
                f"- Users: {counts['users']:,}",
                f"- Train rows: {counts['train']:,}",
                f"- Validation rows: {counts['valid']:,}",
                f"- Test rows: {counts['test']:,}",
                "- Split type: chronological within each user",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"OK: sample written to {sample_path} ({kept_rows:,} rows)")
    print(f"OK: train/valid/test written to {output_dir}")
    print(f"OK: split summary written to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
