from __future__ import annotations

import hashlib
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Mapping, Sequence

from recommender.poster_cache import PosterCache, get_poster_cache
from recommender.tmdb_client import TmdbMovieDetails, normalize_imdb_id


@dataclass
class _Job:
    future: Future[TmdbMovieDetails]
    submitted_at: float
    imdb_id: str | None


class PosterLoader:
    """Return cached posters immediately and fetch missing metadata in the background."""

    def __init__(self, cache: PosterCache, max_workers: int = 4):
        self.cache = cache
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tmdb")
        self._lock = Lock()
        self._jobs: dict[tuple[str, int], _Job] = {}
        self._api_status: dict[str, str] = {}

    @staticmethod
    def _token_key(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _valid_ids(tmdb_ids: Sequence[int | str | None]) -> list[int]:
        ids: list[int] = []
        for value in tmdb_ids:
            try:
                tmdb_id = int(float(value))
            except (ValueError, TypeError):
                continue
            if tmdb_id > 0 and tmdb_id not in ids:
                ids.append(tmdb_id)
        return ids

    def _fetch(
        self, tmdb_id: int, token: str, token_key: str, imdb_id: str | None
    ) -> TmdbMovieDetails:
        try:
            detail = self.cache.get_details(tmdb_id, token=token, imdb_id=imdb_id)
        except Exception:
            detail = TmdbMovieDetails(
                tmdb_id=tmdb_id,
                status="error",
                error_message="Không thể tải thông tin TMDB",
            )

        with self._lock:
            if detail.status == "auth_error":
                self._api_status[token_key] = "auth_error"
            elif detail.status in ("ok", "not_found"):
                self._api_status[token_key] = "connected"
            elif self._api_status.get(token_key) != "connected":
                self._api_status[token_key] = "unavailable"
        return detail

    def snapshot(
        self,
        tmdb_ids: Sequence[int | str | None],
        token: str | None,
        imdb_by_tmdb: Mapping[int, str] | None = None,
    ) -> tuple[dict[int, TmdbMovieDetails], list[int]]:
        """Get details ready for this render and IDs whose background jobs are pending."""
        ids = self._valid_ids(tmdb_ids)
        imdb_by_tmdb = imdb_by_tmdb or {}
        details = self.cache.get_cached_details_batch(ids, imdb_by_tmdb)
        if not token:
            return details, []

        token_key = self._token_key(token)
        pending: list[int] = []
        now = time.monotonic()
        with self._lock:
            for tmdb_id in ids:
                key = (token_key, tmdb_id)
                imdb_id = normalize_imdb_id(imdb_by_tmdb.get(tmdb_id))
                if tmdb_id in details:
                    job = self._jobs.get(key)
                    if job is not None and job.future.done():
                        del self._jobs[key]
                    continue

                job = self._jobs.get(key)
                if job is not None and job.imdb_id != imdb_id:
                    del self._jobs[key]
                    job = None
                if job is not None and job.future.done():
                    result = job.future.result()
                    # Transient failures may be retried after a short pause.
                    if result.status not in ("error", "auth_error") or now - job.submitted_at < 60:
                        details[tmdb_id] = result
                        continue
                    del self._jobs[key]

                if key not in self._jobs:
                    self._jobs[key] = _Job(
                        future=self._executor.submit(
                            self._fetch, tmdb_id, token, token_key, imdb_id
                        ),
                        submitted_at=now,
                        imdb_id=imdb_id,
                    )
                pending.append(tmdb_id)
        return details, pending

    def any_completed(self, tmdb_ids: Sequence[int], token: str | None) -> bool:
        if not token:
            return False
        token_key = self._token_key(token)
        with self._lock:
            return any(
                (job := self._jobs.get((token_key, tmdb_id))) is not None and job.future.done()
                for tmdb_id in tmdb_ids
            )

    def api_status(self, token: str | None) -> str:
        if not token:
            return "no_token"
        with self._lock:
            return self._api_status.get(self._token_key(token), "unchecked")


_GLOBAL_LOADER: PosterLoader | None = None


def get_poster_loader() -> PosterLoader:
    global _GLOBAL_LOADER
    if _GLOBAL_LOADER is None:
        _GLOBAL_LOADER = PosterLoader(get_poster_cache())
    return _GLOBAL_LOADER
