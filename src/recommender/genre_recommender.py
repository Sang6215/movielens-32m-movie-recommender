from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import pandas as pd

# Specification Table 4.2: Exact mapping between MovieLens genres and Vietnamese labels
# IMAX and (no genres listed) are excluded from the main genre selection.
GENRE_MAP_EN_TO_VI: dict[str, str] = {
    "Action": "Hành động",
    "Adventure": "Phiêu lưu",
    "Animation": "Hoạt hình",
    "Children": "Thiếu nhi",
    "Comedy": "Hài",
    "Crime": "Tội phạm",
    "Documentary": "Tài liệu",
    "Drama": "Chính kịch",
    "Fantasy": "Giả tưởng",
    "Film-Noir": "Phim noir",
    "Horror": "Kinh dị",
    "Musical": "Nhạc kịch",
    "Mystery": "Bí ẩn",
    "Romance": "Lãng mạn",
    "Sci-Fi": "Khoa học viễn tưởng",
    "Thriller": "Giật gân",
    "War": "Chiến tranh",
    "Western": "Cao bồi",
}

GENRE_MAP_VI_TO_EN: dict[str, str] = {v: k for k, v in GENRE_MAP_EN_TO_VI.items()}

# Ordered Vietnamese genre labels for UI selection
ALL_GENRES_VI: tuple[str, ...] = tuple(sorted(GENRE_MAP_VI_TO_EN.keys()))
ALL_GENRES_EN: tuple[str, ...] = tuple(sorted(GENRE_MAP_EN_TO_VI.keys()))


def normalize_to_en(genre: str) -> str | None:
    """Normalize input genre string (VI, EN, or 'VI (EN)') to English MovieLens genre token."""
    g = genre.strip()
    # Handle combined format like "Hành động (Action)"
    if "(" in g and g.endswith(")"):
        inner = g[g.rfind("(") + 1 : -1].strip()
        if inner in GENRE_MAP_EN_TO_VI:
            return inner
        outer = g[: g.rfind("(")].strip()
        if outer in GENRE_MAP_VI_TO_EN:
            return GENRE_MAP_VI_TO_EN[outer]

    if g in GENRE_MAP_EN_TO_VI:
        return g
    if g in GENRE_MAP_VI_TO_EN:
        return GENRE_MAP_VI_TO_EN[g]
    # Check case-insensitive match
    for en_name, vi_name in GENRE_MAP_EN_TO_VI.items():
        if g.lower() == en_name.lower() or g.lower() == vi_name.lower():
            return en_name
    return None


def normalize_to_vi(genre: str) -> str:
    """Normalize input genre string (EN or VI) to Vietnamese display label."""
    g = genre.strip()
    if g in GENRE_MAP_VI_TO_EN:
        return g
    if g in GENRE_MAP_EN_TO_VI:
        return GENRE_MAP_EN_TO_VI[g]
    for en_name, vi_name in GENRE_MAP_EN_TO_VI.items():
        if g.lower() == en_name.lower() or g.lower() == vi_name.lower():
            return vi_name
    return g


@dataclass(frozen=True)
class RecommendationResult:
    movies: pd.DataFrame
    total_matched: int
    selected_genres_vi: list[str]
    selected_genres_en: list[str]

    @property
    def has_results(self) -> bool:
        return not self.movies.empty


def recommend_by_genres(
    catalog: pd.DataFrame,
    selected_genres: Sequence[str],
) -> RecommendationResult:
    """Filter and rank movies based on user's selected genres according to the specification.

    Rules:
    1. Normalize selected genres to MovieLens tokens.
    2. Filter movies having at least 1 matching genre, including unrated movies.
    3. Count matched genres per movie.
    4. Rank by:
       - matched_genre_count DESC
       - weighted_score DESC
       - rating_count DESC
       - movieId ASC (deterministic tie-breaker)
    5. Return every matching movie with a recommendation reason.
    """
    if not selected_genres:
        return RecommendationResult(
            movies=pd.DataFrame(),
            total_matched=0,
            selected_genres_vi=[],
            selected_genres_en=[],
        )

    # Normalize selected genres
    en_genres_set = set()
    vi_genres_list = []
    for g in selected_genres:
        en_token = normalize_to_en(g)
        if en_token:
            en_genres_set.add(en_token)
            vi_genres_list.append(GENRE_MAP_EN_TO_VI[en_token])

    if not en_genres_set:
        return RecommendationResult(
            movies=pd.DataFrame(),
            total_matched=0,
            selected_genres_vi=[],
            selected_genres_en=[],
        )

    candidates = catalog.copy()

    # Function to calculate matched genres for a movie
    def get_matches(movie_genres) -> list[str]:
        if movie_genres is None or len(movie_genres) == 0:
            return []
        return [g for g in movie_genres if g in en_genres_set]

    candidates["matched_en"] = candidates["genres"].apply(get_matches)
    candidates["matched_genre_count"] = candidates["matched_en"].apply(len)

    # Filter movies with at least 1 matching genre
    filtered = candidates[candidates["matched_genre_count"] > 0].copy()
    total_matched = len(filtered)

    if total_matched == 0:
        return RecommendationResult(
            movies=pd.DataFrame(),
            total_matched=0,
            selected_genres_vi=vi_genres_list,
            selected_genres_en=list(en_genres_set),
        )

    # Sort according to specification:
    # 1. matched_genre_count DESC
    # 2. weighted_score DESC
    # 3. rating_count DESC
    # 4. movieId ASC
    ranked = filtered.sort_values(
        by=["matched_genre_count", "weighted_score", "rating_count", "movieId"],
        ascending=[False, False, False, True],
        na_position="last",
    )

    # Compute Vietnamese genres and reasons
    ranked["matched_genres_vi"] = ranked["matched_en"].apply(
        lambda genres: [GENRE_MAP_EN_TO_VI[g] for g in genres if g in GENRE_MAP_EN_TO_VI]
    )
    ranked["all_genres_vi"] = ranked["genres"].apply(
        lambda genres: [GENRE_MAP_EN_TO_VI.get(g, g) for g in (genres if genres is not None else []) if g and g != "(no genres listed)"]
    )
    ranked["reason"] = ranked["matched_genres_vi"].apply(
        lambda vi_list: f"Phù hợp: {', '.join(vi_list)}"
    )

    return RecommendationResult(
        movies=ranked,
        total_matched=total_matched,
        selected_genres_vi=vi_genres_list,
        selected_genres_en=list(en_genres_set),
    )
