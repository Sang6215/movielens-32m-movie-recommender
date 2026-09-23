from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping, Sequence

from recommender.config import PROJECT_ROOT
from recommender.tmdb_client import (
    TmdbMovieDetails,
    fetch_movie_from_tmdb,
    get_tmdb_token,
    normalize_imdb_id,
)

DEFAULT_CACHE_DIR = PROJECT_ROOT / "artifacts" / "cache"
DEFAULT_DB_PATH = DEFAULT_CACHE_DIR / "tmdb_cache.db"
DEFAULT_TTL_SECONDS = 7 * 24 * 3600  # 7 days as recommended in specification Section 6.3
PLACEHOLDER_PATH = PROJECT_ROOT / "assets" / "poster_placeholder.svg"


class PosterCache:
    """Disk-backed SQLite cache for TMDB movie details and posters."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH, ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self.db_path = Path(db_path)
        self.ttl_seconds = ttl_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._get_connection()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tmdb_movies (
                    tmdb_id INTEGER PRIMARY KEY,
                    resolved_tmdb_id INTEGER,
                    media_type TEXT,
                    lookup_imdb_id TEXT,
                    title TEXT,
                    title_vi TEXT,
                    overview TEXT,
                    overview_lang TEXT,
                    poster_path TEXT,
                    poster_url TEXT,
                    backdrop_url TEXT,
                    release_date TEXT,
                    vote_average REAL,
                    status TEXT,
                    updated_at REAL
                )
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(tmdb_movies)")}
            for name, sql_type in (
                ("resolved_tmdb_id", "INTEGER"),
                ("media_type", "TEXT"),
                ("lookup_imdb_id", "TEXT"),
            ):
                if name not in columns:
                    conn.execute(f"ALTER TABLE tmdb_movies ADD COLUMN {name} {sql_type}")
            conn.commit()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> TmdbMovieDetails:
        return TmdbMovieDetails(
            tmdb_id=row["tmdb_id"],
            resolved_tmdb_id=row["resolved_tmdb_id"],
            media_type=row["media_type"] or "movie",
            lookup_imdb_id=row["lookup_imdb_id"],
            title=row["title"],
            title_vi=row["title_vi"],
            overview=row["overview"],
            overview_lang=row["overview_lang"],
            poster_path=row["poster_path"],
            poster_url=row["poster_url"],
            backdrop_url=row["backdrop_url"],
            release_date=row["release_date"],
            vote_average=row["vote_average"],
            status=row["status"],
        )

    def get_details(
        self, tmdb_id: int | str | None, token: str | None = None, imdb_id: str | None = None
    ) -> TmdbMovieDetails:
        """Get details for a single tmdb_id, querying cache first."""
        if tmdb_id is None:
            return TmdbMovieDetails(
                tmdb_id=0,
                status="not_found",
                error_message="Không có tmdbId liên kết",
            )

        try:
            clean_id = int(float(tmdb_id))
        except (ValueError, TypeError):
            return TmdbMovieDetails(
                tmdb_id=0,
                status="error",
                error_message=f"tmdbId không hợp lệ: {tmdb_id}",
            )

        clean_imdb_id = normalize_imdb_id(imdb_id)
        now = time.time()
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tmdb_movies WHERE tmdb_id = ?", (clean_id,)
            )
            row = cursor.fetchone()
            if row:
                updated_at = row["updated_at"]
                needs_imdb_retry = (
                    row["status"] == "not_found"
                    and clean_imdb_id
                    and row["lookup_imdb_id"] != clean_imdb_id
                )
                if now - updated_at < self.ttl_seconds and not needs_imdb_retry:
                    return self._from_row(row)

        # Cache miss or expired: fetch from API
        details = fetch_movie_from_tmdb(
            clean_id, token=token or get_tmdb_token(), imdb_id=clean_imdb_id
        )

        # Only store permanent statuses in cache (ok or not_found)
        if details.status in ("ok", "not_found"):
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO tmdb_movies (
                        tmdb_id, resolved_tmdb_id, media_type, lookup_imdb_id,
                        title, title_vi, overview, overview_lang,
                        poster_path, poster_url, backdrop_url, release_date,
                        vote_average, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        details.tmdb_id,
                        details.resolved_tmdb_id,
                        details.media_type,
                        details.lookup_imdb_id,
                        details.title,
                        details.title_vi,
                        details.overview,
                        details.overview_lang,
                        details.poster_path,
                        details.poster_url,
                        details.backdrop_url,
                        details.release_date,
                        details.vote_average,
                        details.status,
                        now,
                    ),
                )
                conn.commit()

        return details

    def get_cached_details_batch(
        self,
        tmdb_ids: Sequence[int | str | None],
        imdb_by_tmdb: Mapping[int, str] | None = None,
    ) -> dict[int, TmdbMovieDetails]:
        """Read only fresh cached details; never wait for the TMDB API."""
        results: dict[int, TmdbMovieDetails] = {}
        valid_ids: list[int] = []

        for tid in tmdb_ids:
            if tid is None:
                continue
            try:
                cid = int(float(tid))
                if cid > 0:
                    valid_ids.append(cid)
            except (ValueError, TypeError):
                continue

        if not valid_ids:
            return results

        now = time.time()
        with self._connection() as conn:
            placeholders = ",".join("?" for _ in valid_ids)
            cursor = conn.execute(
                f"SELECT * FROM tmdb_movies WHERE tmdb_id IN ({placeholders})",
                valid_ids,
            )
            for row in cursor.fetchall():
                cid = row["tmdb_id"]
                imdb_id = normalize_imdb_id((imdb_by_tmdb or {}).get(cid))
                needs_imdb_retry = (
                    row["status"] == "not_found"
                    and imdb_id
                    and row["lookup_imdb_id"] != imdb_id
                )
                if now - row["updated_at"] < self.ttl_seconds and not needs_imdb_retry:
                    results[cid] = self._from_row(row)

        return results

    def get_details_batch(
        self,
        tmdb_ids: Sequence[int | str | None],
        imdb_by_tmdb: Mapping[int, str] | None = None,
    ) -> dict[int, TmdbMovieDetails]:
        """Fetch uncached details synchronously (use only outside interactive rendering)."""
        results = self.get_cached_details_batch(tmdb_ids, imdb_by_tmdb)
        valid_ids: list[int] = []
        for tid in tmdb_ids:
            try:
                cid = int(float(tid))
                if cid > 0 and cid not in valid_ids:
                    valid_ids.append(cid)
            except (ValueError, TypeError):
                continue

        for cid in valid_ids:
            if cid not in results:
                results[cid] = self.get_details(cid, imdb_id=(imdb_by_tmdb or {}).get(cid))

        return results


# Global singleton instance
_GLOBAL_CACHE: PosterCache | None = None


def get_poster_cache() -> PosterCache:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = PosterCache()
    return _GLOBAL_CACHE
