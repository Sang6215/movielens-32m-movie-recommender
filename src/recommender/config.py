from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class DatasetFile:
    name: str
    header: tuple[str, ...]
    expected_rows: int


MOVIELENS_FILES: tuple[DatasetFile, ...] = (
    DatasetFile("ratings.csv", ("userId", "movieId", "rating", "timestamp"), 32_000_204),
    DatasetFile("movies.csv", ("movieId", "title", "genres"), 87_585),
    DatasetFile("tags.csv", ("userId", "movieId", "tag", "timestamp"), 2_000_072),
    DatasetFile("links.csv", ("movieId", "imdbId", "tmdbId"), 87_585),
)


EXPECTED_MD5: dict[str, str] = {
    "links.csv": "8f033867bcb4e6be8792b21468b4fa6e",
    "movies.csv": "0df90835c19151f9d819d0822e190797",
    "ratings.csv": "cf12b74f9ad4b94a011f079e26d4270a",
    "tags.csv": "963bf4fa4de6b8901868fddd3eb54567",
}


def resolve_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
