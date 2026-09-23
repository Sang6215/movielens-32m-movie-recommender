from __future__ import annotations

import hashlib
from pathlib import Path


def count_data_rows(csv_path: Path) -> int:
    with csv_path.open("rb") as handle:
        handle.readline()
        return sum(1 for _ in handle)


def read_header(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        return handle.readline().strip().split(",")


def md5_file(path: Path, chunk_size: int = 16 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
