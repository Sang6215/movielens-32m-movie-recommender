"""FastAPI backend for the React movie catalog.

The Streamlit prototype remains in app.py. This API reads the same MovieLens
catalog and reuses its genre ranking and TMDB poster cache.
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recommender.genre_recommender import (  # noqa: E402
    ALL_GENRES_EN,
    GENRE_MAP_EN_TO_VI,
    normalize_to_en,
    recommend_by_genres,
)
from recommender.als_recommender import ALSRecommender  # noqa: E402
from recommender.poster_cache import PLACEHOLDER_PATH  # noqa: E402
from recommender.poster_loader import get_poster_loader  # noqa: E402
from recommender.tmdb_client import (  # noqa: E402
    TmdbMovieDetails,
    get_tmdb_token,
    normalize_imdb_id,
)

CATALOG_PATH = ROOT / "artifacts" / "catalog" / "movie_catalog.parquet"
MANIFEST_PATH = ROOT / "artifacts" / "catalog" / "manifest.json"
DIST_DIR = ROOT / "frontend" / "dist"
ALS_DIR = ROOT / "artifacts" / "als_serving"
PAGE_SIZE = 24
FEATURED_MOVIE_IDS = (318, 202439, 858, 79132)
POSTER_LOADER = get_poster_loader()
TMDB_TOKEN = get_tmdb_token()

app = FastAPI(title="Cine32 movie catalog", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _file_version(path: Path) -> tuple[int, int]:
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Thiếu catalog: {path.name}")
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=2)
def _load_catalog(version: tuple[int, int]) -> pd.DataFrame:
    return pd.read_parquet(CATALOG_PATH)


def _catalog() -> pd.DataFrame:
    return _load_catalog(_file_version(CATALOG_PATH))


@lru_cache(maxsize=2)
def _load_manifest(version: tuple[int, int]) -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {}
    return _load_manifest(_file_version(MANIFEST_PATH))


@lru_cache(maxsize=1)
def _load_als(artifact_version: tuple[int, int], manifest_version: tuple[int, int], catalog_version: tuple[int, int]) -> ALSRecommender:
    return ALSRecommender(ALS_DIR, _catalog())


def _als() -> ALSRecommender:
    if not (ALS_DIR / "factors_and_history.npz").exists() or not (ALS_DIR / "manifest.json").exists():
        raise HTTPException(status_code=503, detail="Chưa có dữ liệu ALS. Chạy scripts/12_prepare_als_serving.py trước.")
    return _load_als(_file_version(ALS_DIR / "factors_and_history.npz"),
                     _file_version(ALS_DIR / "manifest.json"), _file_version(CATALOG_PATH))


def _optional_int(value: Any) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _list_value(value: Any) -> list[Any]:
    if value is None or isinstance(value, float) and pd.isna(value):
        return []
    return list(value)


def _display_title(title: str) -> str:
    """Remove MovieLens's year suffix and move a trailing English article."""
    title = re.sub(r" \(\d{4}\)$", "", title)
    for article in ("The", "An", "A"):
        suffix = f", {article}"
        if title.endswith(suffix):
            return f"{article} {title[:-len(suffix)]}"
    return title


def _poster_snapshot(
    rows: list[Mapping[str, Any]],
) -> tuple[dict[int, TmdbMovieDetails], set[int]]:
    tmdb_ids = [row.get("tmdbId") for row in rows]
    imdb_by_tmdb = {
        tmdb_id: str(row["imdbId"])
        for row in rows
        if (tmdb_id := _optional_int(row.get("tmdbId"))) is not None
        and pd.notna(row.get("imdbId"))
    }
    details, pending = POSTER_LOADER.snapshot(tmdb_ids, TMDB_TOKEN, imdb_by_tmdb)
    return details, set(pending)


def _movie_payload(
    row: Mapping[str, Any],
    details: dict[int, TmdbMovieDetails],
    pending: set[int],
) -> dict[str, Any]:
    tmdb_id = _optional_int(row.get("tmdbId"))
    detail = details.get(tmdb_id) if tmdb_id is not None else None
    genres_en = _list_value(row.get("genres"))
    matched_vi = _list_value(row.get("matched_genres_vi"))
    imdb_id = normalize_imdb_id(
        str(row["imdbId"]) if pd.notna(row.get("imdbId")) else None
    )
    payload = {
        "movieId": int(row["movieId"]),
        "title": str(row["title"]),
        "displayTitle": _display_title(str(row["title"])),
        "year": _optional_int(row.get("year")),
        "genres": genres_en,
        "genresVi": [GENRE_MAP_EN_TO_VI.get(genre, genre) for genre in genres_en if genre != "(no genres listed)"],
        "matchedGenresVi": matched_vi,
        "rating": _optional_float(row.get("avg_rating")),
        "ratingCount": int(row.get("rating_count") or 0),
        "posterUrl": detail.poster_url if detail and detail.poster_url else "/media/poster-placeholder.svg",
        "backdropUrl": detail.backdrop_url if detail else None,
        "posterPending": tmdb_id in pending if tmdb_id is not None else False,
        "overview": detail.overview if detail else None,
        "overviewLang": detail.overview_lang if detail else None,
        "titleVi": detail.title_vi if detail else None,
        "tmdbUrl": detail.web_url if detail and detail.status == "ok" else None,
        "imdbUrl": f"https://www.imdb.com/title/tt{imdb_id}/" if imdb_id else None,
    }
    if "prediction" in row:
        payload["predictionScore"] = _optional_float(row.get("prediction"))
    if "rank" in row:
        payload["personalRank"] = _optional_int(row.get("rank"))
    if "history_rating" in row:
        payload["historyRating"] = _optional_float(row.get("history_rating"))
    return payload


def _serialize_rows(rows: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    details, pending = _poster_snapshot(rows)
    return [_movie_payload(row, details, pending) for row in rows], len(pending)


def select_movies(
    catalog: pd.DataFrame, selected_genres: list[str], search: str = ""
) -> pd.DataFrame:
    """Return every matching catalog row in stable ranking order."""
    if selected_genres:
        ranked = recommend_by_genres(catalog, selected_genres).movies
    else:
        ranked = catalog.sort_values(
            ["weighted_score", "rating_count", "movieId"],
            ascending=[False, False, True],
            na_position="last",
        )
    if search.strip():
        term = search.strip()
        titles = ranked["title"].astype(str)
        display_titles = titles.str.replace(r" \(\d{4}\)$", "", regex=True).str.replace(
            r"^(.*), (The|An|A)$", r"\2 \1", regex=True
        )
        ranked = ranked[
            titles.str.contains(term, case=False, regex=False, na=False)
            | display_titles.str.contains(term, case=False, regex=False, na=False)
        ]
    return ranked


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    catalog = _catalog()
    manifest = _manifest()
    return {
        "genres": [{"id": genre, "label": GENRE_MAP_EN_TO_VI[genre]} for genre in ALL_GENRES_EN],
        "totalMovies": len(catalog),
        "moviesWithRatings": int(manifest.get("movies_with_ratings", 0)),
        "ratingCount": int(manifest.get("total_ratings", 0)),
        "tmdbConfigured": bool(TMDB_TOKEN),
    }


@app.get("/api/featured")
def featured() -> dict[str, Any]:
    catalog = _catalog()
    rows = (
        catalog[catalog["movieId"].isin(FEATURED_MOVIE_IDS)]
        .set_index("movieId")
        .loc[list(FEATURED_MOVIE_IDS)]
        .reset_index()
        .to_dict(orient="records")
    )
    items, pending = _serialize_rows(rows)
    return {"items": items, "pendingPosters": pending}


@app.get("/api/als/meta")
def als_meta() -> dict[str, Any]:
    engine = _als()
    return {
        "users": len(engine.user_ids),
        "candidateMovies": len(engine.item_ids),
        "minRatingCount": engine.manifest["min_rating_count"],
        "topK": engine.manifest["top_k"],
        "selectedParams": engine.manifest["selected_params"],
        "testRatingMetrics": engine.manifest["test_rating_metrics"],
        "exampleUserIds": [int(uid) for uid in engine.user_ids[:5]],
    }


@app.get("/api/als/recommendations")
def personal_recommendations(user_id: int = Query(ge=0, le=2_147_483_647)) -> dict[str, Any]:
    result = _als().recommend(user_id)
    items, pending = _serialize_rows(result.movies.to_dict(orient="records"))
    history, history_pending = _serialize_rows(result.history.to_dict(orient="records"))
    return {
        "userId": user_id, "knownUser": result.known_user,
        "strategy": "als" if result.known_user else "weighted_score_fallback",
        "items": items, "history": history, "historyCount": result.history_count,
        "pendingPosters": pending + history_pending,
        "message": "Top 10 phim chưa được người dùng đánh giá."
                   if result.known_user else "Người dùng chưa có lịch sử trong mô hình. Hiển thị phim được cộng đồng đánh giá cao.",
    }


@app.get("/api/movies")
def movies(
    genres: list[str] | None = Query(default=None),
    search: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1),
) -> dict[str, Any]:
    selected = list(dict.fromkeys(genres or []))
    invalid = [genre for genre in selected if normalize_to_en(genre) is None]
    if invalid:
        raise HTTPException(status_code=422, detail=f"Thể loại không hợp lệ: {', '.join(invalid)}")
    ranked = select_movies(_catalog(), selected, search)
    total = len(ranked)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    current_page = min(page, total_pages) if total_pages else 1
    start = (current_page - 1) * PAGE_SIZE
    rows = ranked.iloc[start : start + PAGE_SIZE].to_dict(orient="records")
    items, pending = _serialize_rows(rows)
    return {
        "items": items,
        "total": total,
        "page": current_page,
        "pageSize": PAGE_SIZE,
        "totalPages": total_pages,
        "pendingPosters": pending,
    }


@app.get("/api/posters")
def posters(movie_ids: list[int] = Query(default=[])) -> dict[str, Any]:
    if len(movie_ids) > 40:
        raise HTTPException(status_code=422, detail="Tối đa 40 phim mỗi lần tải poster")
    catalog = _catalog()
    rows = catalog[catalog["movieId"].isin(set(movie_ids))].to_dict(orient="records")
    items, pending = _serialize_rows(rows)
    return {"items": items, "pendingPosters": pending}


@app.get("/media/poster-placeholder.svg", include_in_schema=False)
def placeholder() -> FileResponse:
    return FileResponse(PLACEHOLDER_PATH, media_type="image/svg+xml")


if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def frontend_not_built() -> dict[str, str]:
        return {"message": "Chạy npm install và npm run build trong thư mục frontend."}
