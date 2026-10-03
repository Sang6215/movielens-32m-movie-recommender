"""Install the checksum-pinned public demo artifacts into a clean project folder.

Uses the Python standard library; never reads or copies TMDB credentials.
Existing files are preserved. No training, Spark, Hadoop or Node.js is needed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE_URL = (
    "https://github.com/Sang6215/movielens-32m-movie-recommender/"
    "releases/download/v1.0.0/cine32-demo-v1.0.0.zip"
)
RELEASE_SHA256 = "cf2eeb18e02af159ebcdb70c356fda9016af30a5cf194f8437ee9fc7672a8ab7"
MAX_DOWNLOAD_BYTES = 128 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 160 * 1024 * 1024
MANIFEST_NAME = "DEMO_PACKAGE_MANIFEST.json"
EXPECTED_FILES = frozenset({
    "artifacts/catalog/movie_catalog.parquet",
    "artifacts/catalog/manifest.json",
    "artifacts/als_serving/factors_and_history.npz",
    "artifacts/als_serving/manifest.json",
    "frontend/dist/index.html",
    "frontend/dist/favicon.svg",
    "frontend/dist/assets/index-Bc8vw7L-.js",
    "frontend/dist/assets/index-DRxoOaUm.css",
    "licenses/MovieLens32M_README.txt",
    "DEMO_README.md",
    MANIFEST_NAME,
})
CHUNK_BYTES = 1024 * 1024


def _check_plain_path(path: Path) -> None:
    """Reject links, including Windows junctions, before resolving any target."""
    for part in (path, *path.parents):
        is_junction = getattr(part, "is_junction", lambda: False)
        if part.is_symlink() or is_junction():
            raise ValueError(f"Refusing linked output path: {part}")


def _output_root(path: Path) -> Path:
    absolute = path.absolute()
    _check_plain_path(absolute)
    root = absolute.resolve()
    if root == Path(root.anchor):
        raise ValueError("Output must be a project folder, not a filesystem root")
    if root.exists() and not root.is_dir():
        raise ValueError(f"Output is not a directory: {root}")
    return root


def _target(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if (
        name not in EXPECTED_FILES or relative.is_absolute()
        or ".." in relative.parts or "\\" in name or ":" in name
    ):
        raise ValueError(f"Unexpected or unsafe archive member: {name}")
    target = root.joinpath(*relative.parts)
    _check_plain_path(target)
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"Archive member escaped output folder: {name}")
    return target


def _preflight(root: Path) -> None:
    for name in sorted(EXPECTED_FILES):
        target = _target(root, name)
        if target.exists():
            raise FileExistsError(f"Existing file preserved; choose a clean output folder: {target}")
        for parent in target.parents:
            if parent == root:
                break
            if parent.exists() and not parent.is_dir():
                raise ValueError(f"Output parent is not a directory: {parent}")


def _download(destination: Path) -> None:
    request = urllib.request.Request(RELEASE_URL, headers={"User-Agent": "CINE32-demo-installer/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("xb") as output:
        total = 0
        while block := response.read(CHUNK_BYTES):
            total += len(block)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("Release download exceeds the size limit")
            output.write(block)


def _verify_archive(path: Path) -> None:
    if path.stat().st_size > MAX_DOWNLOAD_BYTES:
        raise ValueError("Release archive exceeds the size limit")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != RELEASE_SHA256:
        raise ValueError("Release SHA256 mismatch; no artifacts were installed")


def _stage_archive(path: Path, stage: Path, root: Path) -> list[str]:
    """Verify each entry before any permanent file is written."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(set(names)) != len(names) or set(names) != EXPECTED_FILES:
            raise ValueError("Release archive contains missing, duplicate or unexpected files")
        if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Release archive exceeds the uncompressed size limit")
        for entry in entries:
            _target(root, entry.filename)
            file_type = stat.S_IFMT(entry.external_attr >> 16)
            if entry.is_dir() or file_type not in (0, stat.S_IFREG) or entry.flag_bits & 1:
                raise ValueError(f"Archive member is not a regular unencrypted file: {entry.filename}")
        if archive.getinfo(MANIFEST_NAME).file_size > 64 * 1024:
            raise ValueError("Release manifest exceeds the size limit")
        manifest = json.loads(archive.read(MANIFEST_NAME))
        if manifest.get("format_version") != 1 or manifest.get("release") != "v1.0.0":
            raise ValueError("Unsupported demo release manifest")
        file_records = manifest.get("files")
        if not isinstance(file_records, dict) or set(file_records) != EXPECTED_FILES - {MANIFEST_NAME}:
            raise ValueError("Release manifest does not match the allowlist")
        for entry in entries:
            staged = stage.joinpath(*PurePosixPath(entry.filename).parts)
            staged.parent.mkdir(parents=True, exist_ok=True)
            digest, size = hashlib.sha256(), 0
            with archive.open(entry) as source, staged.open("xb") as output:
                while block := source.read(CHUNK_BYTES):
                    size += len(block)
                    if size > entry.file_size:
                        raise ValueError(f"Archive member exceeds declared size: {entry.filename}")
                    digest.update(block)
                    output.write(block)
            if size != entry.file_size:
                raise ValueError(f"Archive member size mismatch: {entry.filename}")
            if entry.filename != MANIFEST_NAME:
                record = file_records[entry.filename]
                if (
                    not isinstance(record, dict)
                    or record.get("bytes") != size
                    or not isinstance(record.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                    or record["sha256"] != digest.hexdigest()
                ):
                    raise ValueError(f"Release member checksum mismatch: {entry.filename}")
    return names


def install(output_dir: Path, archive_path: Path | None = None) -> dict[str, object]:
    root = _output_root(output_dir)
    _preflight(root)
    root.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="cine32-install-") as temporary:
        temporary_root = Path(temporary)
        archive = archive_path
        if archive is None:
            archive = temporary_root / "cine32-demo-v1.0.0.zip"
            _download(archive)
        _verify_archive(archive)
        names = _stage_archive(archive, temporary_root / "staged", root)
        _preflight(root)
        try:
            for name in names:
                target = _target(root, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    created.append(target)
                    with (temporary_root / "staged" / name).open("rb") as source:
                        shutil.copyfileobj(source, output, length=CHUNK_BYTES)
        except Exception:
            # Remove only files created by this invocation, never pre-existing data.
            for target in reversed(created):
                target.unlink(missing_ok=True)
            raise
    return {"release": "v1.0.0", "sha256": RELEASE_SHA256, "files": len(names), "output_dir": str(root)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="Clean project folder (default: project root)")
    parser.add_argument("--archive", type=Path, help="Use a local release ZIP instead of downloading; SHA256 is still required")
    args = parser.parse_args()
    try:
        result = install(args.output_dir, args.archive)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Installation failed: {error}\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
