from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from recommender.config import EXPECTED_MD5, MOVIELENS_FILES, resolve_path
from recommender.local_io import count_data_rows, md5_file, read_header


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate MovieLens 32M raw CSV files.")
    parser.add_argument("--data-dir", default="ml-32m", help="Folder containing MovieLens CSV files.")
    parser.add_argument("--skip-md5", action="store_true", help="Skip checksum validation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = resolve_path(args.data_dir)
    failures: list[str] = []

    print(f"Checking raw data in: {data_dir}")

    for spec in MOVIELENS_FILES:
        path = data_dir / spec.name
        if not path.exists():
            failures.append(f"{spec.name}: missing")
            continue

        header = read_header(path)
        rows = count_data_rows(path)
        expected_header = list(spec.header)

        header_ok = header == expected_header
        rows_ok = rows == spec.expected_rows
        md5_ok = True
        checksum = "skipped"

        if not args.skip_md5:
            checksum = md5_file(path)
            md5_ok = checksum == EXPECTED_MD5[spec.name]

        print(
            f"{spec.name}: rows={rows:,} "
            f"header_ok={header_ok} rows_ok={rows_ok} md5_ok={md5_ok}"
        )

        if not header_ok:
            failures.append(f"{spec.name}: header {header} != {expected_header}")
        if not rows_ok:
            failures.append(f"{spec.name}: rows {rows:,} != {spec.expected_rows:,}")
        if not md5_ok:
            failures.append(f"{spec.name}: md5 {checksum} != {EXPECTED_MD5[spec.name]}")

    if failures:
        print("\nFAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nOK: MovieLens 32M raw dataset is complete and matches expected checksums.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
