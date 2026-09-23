"""Add IMDb IDs to an existing movie catalog without recomputing 32M ratings."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "artifacts" / "catalog" / "movie_catalog.parquet"
MANIFEST_PATH = ROOT / "artifacts" / "catalog" / "manifest.json"
LINKS_PATH = ROOT / "data" / "processed" / "parquet" / "links.parquet"


def main() -> None:
    if not CATALOG_PATH.exists() or not LINKS_PATH.exists():
        raise FileNotFoundError("Cần có movie_catalog.parquet và links.parquet trước khi bổ sung IMDb ID")

    catalog = pd.read_parquet(CATALOG_PATH)
    if "imdbId" not in catalog.columns:
        links = pd.read_parquet(LINKS_PATH, columns=["movieId", "imdbId"])
        links["imdbId"] = links["imdbId"].astype("string")
        catalog = catalog.merge(links, on="movieId", how="left", validate="one_to_one")
        if catalog["imdbId"].isna().any():
            raise ValueError("Có phim trong catalog không tìm được IMDb ID ở links.parquet")

        temporary_catalog = CATALOG_PATH.with_name("movie_catalog.imdb.tmp.parquet")
        catalog.to_parquet(temporary_catalog, index=False)
        temporary_catalog.replace(CATALOG_PATH)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    manifest["columns"] = list(catalog.columns)
    manifest["imdb_enriched_at_utc"] = datetime.now(timezone.utc).isoformat()
    temporary_manifest = MANIFEST_PATH.with_name("manifest.imdb.tmp.json")
    temporary_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_manifest.replace(MANIFEST_PATH)
    print(f"Catalog ready: {len(catalog):,} movies, {catalog['imdbId'].notna().sum():,} IMDb IDs")


if __name__ == "__main__":
    main()
