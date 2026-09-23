from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from typing import Any
import requests

from recommender.config import PROJECT_ROOT

# Use api.tmdb.org as primary to bypass ISP SNI blocks in Vietnam
TMDB_API_BASE_URLS = [
    "https://api.tmdb.org/3",
    "https://api.themoviedb.org/3",
]
TMDB_API_BASE_URL = TMDB_API_BASE_URLS[0]
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_TIMEOUT_SECONDS = 5.0


@dataclass
class TmdbMovieDetails:
    tmdb_id: int
    resolved_tmdb_id: int | None = None
    media_type: str = "movie"
    lookup_imdb_id: str | None = None
    title: str | None = None
    title_vi: str | None = None
    overview: str | None = None
    overview_lang: str | None = None
    poster_path: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    status: str = "ok"  # "ok", "no_token", "not_found", "auth_error", "error"
    error_message: str | None = None

    @property
    def web_url(self) -> str:
        return f"https://www.themoviedb.org/{self.media_type}/{self.resolved_tmdb_id or self.tmdb_id}"


def normalize_imdb_id(imdb_id: str | None) -> str | None:
    if imdb_id is None:
        return None
    digits = str(imdb_id).strip().removeprefix("tt")
    return digits if digits.isdigit() else None


def _find_by_imdb(
    tmdb_id: int,
    imdb_id: str,
    headers: dict[str, str],
    timeout: float,
) -> TmdbMovieDetails:
    """Resolve a stale MovieLens TMDB movie link via its exact IMDb identifier."""
    last_error: Exception | None = None
    for base_url in TMDB_API_BASE_URLS:
        try:
            response = requests.get(
                f"{base_url}/find/tt{imdb_id}",
                params={"external_source": "imdb_id", "language": "vi-VN"},
                headers=headers,
                timeout=timeout,
            )
            if response.status_code in (401, 403):
                return TmdbMovieDetails(tmdb_id=tmdb_id, status="auth_error", lookup_imdb_id=imdb_id)
            if response.status_code == 429:
                return TmdbMovieDetails(tmdb_id=tmdb_id, status="error", error_message="TMDB giới hạn số request")
            response.raise_for_status()
            data = response.json()
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
            last_error = error
        except requests.exceptions.RequestException as error:
            return TmdbMovieDetails(tmdb_id=tmdb_id, status="error", error_message=str(error))
    else:
        return TmdbMovieDetails(tmdb_id=tmdb_id, status="error", error_message=str(last_error))

    matches = [("movie", item) for item in data.get("movie_results", [])]
    matches.extend(("tv", item) for item in data.get("tv_results", []))
    if len(matches) != 1:
        return TmdbMovieDetails(tmdb_id=tmdb_id, status="not_found", lookup_imdb_id=imdb_id)

    media_type, item = matches[0]
    resolved_id = item.get("id")
    if not isinstance(resolved_id, int) or resolved_id <= 0:
        return TmdbMovieDetails(tmdb_id=tmdb_id, status="not_found", lookup_imdb_id=imdb_id)

    overview = item.get("overview")
    overview_lang = "vi" if overview else None
    if not overview:
        try:
            response_en = requests.get(
                f"{base_url}/{media_type}/{resolved_id}",
                params={"language": "en-US"},
                headers=headers,
                timeout=timeout,
            )
            if response_en.status_code == 200:
                overview = response_en.json().get("overview")
                overview_lang = "en" if overview else None
        except requests.exceptions.RequestException:
            pass

    poster_path = item.get("poster_path")
    backdrop_path = item.get("backdrop_path")
    return TmdbMovieDetails(
        tmdb_id=tmdb_id,
        resolved_tmdb_id=resolved_id,
        media_type=media_type,
        lookup_imdb_id=imdb_id,
        title=item.get("original_title") or item.get("original_name") or item.get("title") or item.get("name"),
        title_vi=item.get("title") or item.get("name"),
        overview=overview,
        overview_lang=overview_lang,
        poster_path=poster_path,
        poster_url=f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None,
        backdrop_url=f"{TMDB_IMAGE_BASE_URL}{backdrop_path}" if backdrop_path else None,
        release_date=item.get("release_date") or item.get("first_air_date"),
        vote_average=item.get("vote_average"),
        status="ok",
    )


def get_tmdb_token() -> str | None:
    """Read the TMDB token without depending on a particular web framework."""
    token = os.environ.get("TMDB_READ_ACCESS_TOKEN", "").strip()
    if token and token != "YOUR_TMDB_READ_ACCESS_TOKEN_HERE":
        return token

    secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        try:
            config = tomllib.loads(secrets_path.read_text(encoding="utf-8"))
            token = str(config.get("TMDB_READ_ACCESS_TOKEN", "")).strip()
            if token and token != "YOUR_TMDB_READ_ACCESS_TOKEN_HERE":
                return token
        except (OSError, tomllib.TOMLDecodeError):
            pass

    return None


def fetch_movie_from_tmdb(
    tmdb_id: int | str,
    token: str | None = None,
    timeout: float = TMDB_TIMEOUT_SECONDS,
    imdb_id: str | None = None,
) -> TmdbMovieDetails:
    """Fetch movie details from TMDB API with vi-VN language and fallback to en-US."""
    try:
        clean_id = int(float(tmdb_id))
    except (ValueError, TypeError):
        return TmdbMovieDetails(
            tmdb_id=0,
            status="error",
            error_message=f"Invalid tmdbId: {tmdb_id}",
        )

    clean_imdb_id = normalize_imdb_id(imdb_id)
    auth_token = token or get_tmdb_token()
    if not auth_token:
        return TmdbMovieDetails(
            tmdb_id=clean_id,
            status="no_token",
            error_message="Chưa cấu hình TMDB_READ_ACCESS_TOKEN",
        )

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Accept": "application/json",
    }

    last_error: Exception | None = None
    data: dict[str, Any] | None = None
    base_url_used: str = TMDB_API_BASE_URLS[0]

    for base_url in TMDB_API_BASE_URLS:
        url_vi = f"{base_url}/movie/{clean_id}?language=vi-VN"
        try:
            resp = requests.get(url_vi, headers=headers, timeout=timeout)
            if resp.status_code == 404:
                if clean_imdb_id:
                    return _find_by_imdb(clean_id, clean_imdb_id, headers, timeout)
                return TmdbMovieDetails(
                    tmdb_id=clean_id,
                    status="not_found",
                    error_message="Không tìm thấy phim trên TMDB",
                )
            if resp.status_code in (401, 403):
                return TmdbMovieDetails(
                    tmdb_id=clean_id,
                    status="auth_error",
                    error_message="TMDB từ chối token truy cập",
                )
            if resp.status_code == 429:
                return TmdbMovieDetails(
                    tmdb_id=clean_id,
                    status="error",
                    error_message="Giới hạn số request TMDB (HTTP 429)",
                )
            resp.raise_for_status()
            data = resp.json()
            base_url_used = base_url
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_error = e
            continue
        except requests.exceptions.RequestException as e:
            return TmdbMovieDetails(
                tmdb_id=clean_id,
                status="error",
                error_message=f"Lỗi kết nối TMDB: {e}",
            )

    if data is None:
        return TmdbMovieDetails(
            tmdb_id=clean_id,
            status="error",
            error_message=f"Không thể kết nối đến máy chủ TMDB: {last_error}",
        )

    try:
        overview = data.get("overview")
        overview_lang = "vi" if overview else None
        title_vi = data.get("title")

        # If Vietnamese overview is missing, try English
        if not overview:
            url_en = f"{base_url_used}/movie/{clean_id}?language=en-US"
            try:
                resp_en = requests.get(url_en, headers=headers, timeout=timeout)
                if resp_en.status_code == 200:
                    data_en = resp_en.json()
                    if data_en.get("overview"):
                        overview = data_en.get("overview")
                        overview_lang = "en"
            except Exception:
                pass

        poster_path = data.get("poster_path")
        poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None
        backdrop_path = data.get("backdrop_path")
        backdrop_url = f"{TMDB_IMAGE_BASE_URL}{backdrop_path}" if backdrop_path else None

        return TmdbMovieDetails(
            tmdb_id=clean_id,
            title=data.get("original_title") or data.get("title"),
            title_vi=title_vi,
            overview=overview if overview else None,
            overview_lang=overview_lang,
            poster_path=poster_path,
            poster_url=poster_url,
            backdrop_url=backdrop_url,
            release_date=data.get("release_date"),
            vote_average=data.get("vote_average"),
            status="ok",
        )

    except requests.exceptions.Timeout:
        return TmdbMovieDetails(
            tmdb_id=clean_id,
            status="error",
            error_message="Hết thời gian chờ kết nối TMDB (timeout)",
        )
    except requests.exceptions.RequestException as e:
        return TmdbMovieDetails(
            tmdb_id=clean_id,
            status="error",
            error_message=f"Lỗi kết nối TMDB: {e}",
        )
    except Exception as e:
        return TmdbMovieDetails(
            tmdb_id=clean_id,
            status="error",
            error_message=f"Lỗi xử lý TMDB: {e}",
        )
