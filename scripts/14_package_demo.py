"""Package the existing CINE32 web artifacts without retraining or copying secrets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/releases/cine32-demo-v1.0.0.zip")
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to(ROOT / "artifacts/releases"):
        parser.error("Output must stay inside artifacts/releases/")
    if output.exists():
        parser.error("Output already exists; choose a different --output filename")

    serving = ROOT / "artifacts/als_serving"
    catalog_path = ROOT / "artifacts/catalog/movie_catalog.parquet"
    serving_manifest = json.loads((serving / "manifest.json").read_text(encoding="utf-8"))
    catalog_manifest = json.loads((ROOT / "artifacts/catalog/manifest.json").read_text(encoding="utf-8"))
    catalog = pd.read_parquet(catalog_path, columns=["movieId", "rating_count"])
    with np.load(serving / "factors_and_history.npz", allow_pickle=False) as arrays:
        user_ids, item_ids = arrays["user_ids"], arrays["item_ids"]
        users, items = len(user_ids), len(item_ids)
        history_rows = len(arrays["history_movie_ids"])
        rank = serving_manifest["selected_params"]["rank"]
        assert arrays["user_factors"].shape == (users, rank), "User vector shape mismatch"
        assert arrays["item_factors"].shape == (items, rank), "Item vector shape mismatch"
        assert np.isfinite(arrays["user_factors"]).all(), "Nonfinite user factors"
        assert np.isfinite(arrays["item_factors"]).all(), "Nonfinite item factors"
        assert len(arrays["history_ratings"]) == history_rows, "History length mismatch"
        assert len(arrays["history_starts"]) == users == len(arrays["history_ends"]), "Index length mismatch"
        assert int(arrays["history_ends"][-1]) == history_rows, "History index is incomplete"
    assert users == serving_manifest["users"], "User count mismatch"
    assert items == serving_manifest["items"], "Item count mismatch"
    assert history_rows == serving_manifest["history_rows"], "History count mismatch"
    assert len(catalog) == catalog_manifest["total_movies"], "Catalog count mismatch"
    assert catalog["movieId"].is_unique, "Catalog contains duplicate IDs"
    candidates = catalog[(catalog["rating_count"] >= serving_manifest["min_rating_count"]) & catalog["movieId"].isin(item_ids)]
    assert len(candidates) == serving_manifest["candidate_movies"], "Candidate count mismatch"

    files = {str(p): ROOT / p for p in [
        "artifacts/catalog/movie_catalog.parquet", "artifacts/catalog/manifest.json",
        "artifacts/als_serving/factors_and_history.npz", "artifacts/als_serving/manifest.json",
    ]}
    dist = ROOT / "frontend/dist"
    assert (dist / "index.html").is_file(), "Build frontend first"
    for file in sorted(dist.rglob("*")):
        if file.is_file():
            assert file.suffix in {".html", ".js", ".css", ".svg"}, "Unexpected frontend file"
            files[file.relative_to(ROOT).as_posix()] = file
    files["licenses/MovieLens32M_README.txt"] = ROOT / "ml-32m/README.txt"
    files["DEMO_README.md"] = ROOT / "HUONG_DAN_CHAY_DEMO.md"
    for file in files.values():
        assert file.is_file() and not file.is_symlink(), "Missing or symlinked input"
        assert file.resolve().is_relative_to(ROOT), "Input escaped project root"
    manifest = {
        "format_version": 1, "release": "v1.0.0", "purpose": "CINE32 web inference demo",
        "users": users, "items": items, "catalog_movies": len(catalog),
        "candidate_movies": len(candidates), "history_rows": history_rows,
        "selected_params": serving_manifest["selected_params"],
        "history_policy": serving_manifest["history_policy"],
        "files": {name: {"bytes": file.stat().st_size, "sha256": sha256(file)} for name, file in files.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, file in files.items():
            archive.write(file, name)
        archive.writestr("DEMO_PACKAGE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None, "Archive CRC validation failed"
        for name, expected in manifest["files"].items():
            with archive.open(name) as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            assert digest == expected["sha256"], "Archive content differs from source"
    checksum_path = output.parent / "SHA256SUMS.txt"
    checksum_path.write_text(f"{sha256(output)}  {output.name}\n", encoding="ascii")
    print(json.dumps({"archive": str(output), "bytes": output.stat().st_size,
                      "sha256": sha256(output), "files": len(files) + 1,
                      "users": users, "candidate_movies": len(candidates)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
