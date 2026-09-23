from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recommender.poster_loader import PosterLoader
from recommender.poster_cache import PosterCache
from recommender.tmdb_client import TmdbMovieDetails, fetch_movie_from_tmdb


class SlowCache:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.calls = 0

    def get_cached_details_batch(self, tmdb_ids, imdb_by_tmdb=None):
        return {}

    def get_details(self, tmdb_id, token=None, imdb_id=None):
        self.calls += 1
        self.started.set()
        self.release.wait(timeout=3)
        return TmdbMovieDetails(tmdb_id=tmdb_id, poster_url="https://image.tmdb.org/example", status="ok")


class PosterLoaderTests(unittest.TestCase):
    def test_uncached_poster_does_not_block_movie_cards(self) -> None:
        cache = SlowCache()
        loader = PosterLoader(cache, max_workers=1)
        self.addCleanup(loader._executor.shutdown, wait=True)
        self.addCleanup(cache.release.set)

        started = time.perf_counter()
        details, pending = loader.snapshot([101, 101], "test-token")
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.5)
        self.assertEqual(details, {})
        self.assertEqual(pending, [101])
        self.assertTrue(cache.started.wait(timeout=2))
        self.assertEqual(loader.api_status("test-token"), "unchecked")

        cache.release.set()
        deadline = time.monotonic() + 2
        while not loader.any_completed([101], "test-token") and time.monotonic() < deadline:
            time.sleep(0.01)

        details, pending = loader.snapshot([101], "test-token")
        self.assertEqual(pending, [])
        self.assertEqual(details[101].poster_url, "https://image.tmdb.org/example")
        self.assertEqual(cache.calls, 1)
        self.assertEqual(loader.api_status("test-token"), "connected")

    def test_missing_token_never_starts_network_job(self) -> None:
        cache = SlowCache()
        loader = PosterLoader(cache, max_workers=1)
        self.addCleanup(loader._executor.shutdown, wait=True)

        self.assertEqual(loader.snapshot([101], None), ({}, []))
        self.assertEqual(loader.api_status(None), "no_token")
        self.assertEqual(cache.calls, 0)

    @patch("recommender.tmdb_client.requests.get")
    def test_invalid_token_is_not_reported_as_connected(self, get: Mock) -> None:
        get.return_value.status_code = 401
        result = fetch_movie_from_tmdb(101, token="invalid")
        self.assertEqual(result.status, "auth_error")

    @patch("recommender.tmdb_client.requests.get")
    def test_imdb_fallback_resolves_correct_tv_poster(self, get: Mock) -> None:
        movie_404 = Mock(status_code=404)
        imdb_match = Mock(status_code=200)
        imdb_match.json.return_value = {
            "movie_results": [],
            "tv_results": [
                {
                    "id": 68595,
                    "name": "Planet Earth II",
                    "original_name": "Planet Earth II",
                    "overview": "Thiên nhiên",
                    "poster_path": "/planet.jpg",
                }
            ],
        }
        get.side_effect = [movie_404, imdb_match]

        result = fetch_movie_from_tmdb(420714, token="test-token", imdb_id="5491994")

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.tmdb_id, 420714)
        self.assertEqual(result.resolved_tmdb_id, 68595)
        self.assertEqual(result.web_url, "https://www.themoviedb.org/tv/68595")
        self.assertTrue(result.poster_url.endswith("/planet.jpg"))
        self.assertEqual(get.call_count, 2)

    def test_old_not_found_cache_is_retried_when_imdb_id_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = PosterCache(Path(directory) / "posters.db")
            with cache._connection() as connection:
                connection.execute(
                    "INSERT INTO tmdb_movies (tmdb_id, status, updated_at) VALUES (?, ?, ?)",
                    (420714, "not_found", time.time()),
                )
            self.assertEqual(cache.get_cached_details_batch([420714], {420714: "5491994"}), {})

            resolved = TmdbMovieDetails(
                tmdb_id=420714,
                resolved_tmdb_id=68595,
                media_type="tv",
                lookup_imdb_id="5491994",
                poster_url="https://image.tmdb.org/t/p/w500/planet.jpg",
                status="ok",
            )
            with patch("recommender.poster_cache.fetch_movie_from_tmdb", return_value=resolved) as fetch:
                detail = cache.get_details(420714, token="test-token", imdb_id="5491994")

            self.assertEqual(detail.web_url, "https://www.themoviedb.org/tv/68595")
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(
                cache.get_cached_details_batch([420714], {420714: "5491994"})[420714].web_url,
                "https://www.themoviedb.org/tv/68595",
            )


if __name__ == "__main__":
    unittest.main()
