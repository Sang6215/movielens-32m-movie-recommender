from __future__ import annotations

import json
import html
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# Setup system path for internal modules
ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

from recommender.genre_recommender import (
    ALL_GENRES_EN,
    GENRE_MAP_EN_TO_VI,
    RecommendationResult,
    recommend_by_genres,
)
from recommender.poster_cache import PLACEHOLDER_PATH
from recommender.poster_loader import get_poster_loader
from recommender.tmdb_client import TmdbMovieDetails, get_tmdb_token

CATALOG_PATH = ROOT / "artifacts" / "catalog" / "movie_catalog.parquet"
CATALOG_MANIFEST_PATH = ROOT / "artifacts" / "catalog" / "manifest.json"
ALS_MANIFEST_PATH = ROOT / "artifacts" / "demo" / "manifest.json"
PAGE_SIZE = 24

st.set_page_config(
    page_title="Hôm nay bạn muốn xem phim gì? - MovieLens 32M",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for polished card layout and genre tags
st.markdown(
    """
    <style>
    /* Card title container styling */
    .movie-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        line-height: 1.35;
        margin-top: 0.5rem;
        margin-bottom: 0.25rem;
        min-height: 2.8rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .poster-loading {
        width: 100%;
        aspect-ratio: 2 / 3;
        border: 1px dashed #475569;
        border-radius: 0.5rem;
        background: #1e293b;
        color: #cbd5e1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        text-align: center;
    }
    .poster-loading-icon { font-size: 2rem; }
    .genre-tag-matched {
        display: inline-block;
        background-color: #059669;
        color: #ffffff;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.15rem 0.45rem;
        border-radius: 9999px;
        margin-right: 0.25rem;
        margin-bottom: 0.25rem;
    }
    .genre-tag-neutral {
        display: inline-block;
        background-color: #334155;
        color: #cbd5e1;
        font-size: 0.72rem;
        padding: 0.15rem 0.45rem;
        border-radius: 9999px;
        margin-right: 0.25rem;
        margin-bottom: 0.25rem;
    }
    .rating-badge {
        font-size: 0.95rem;
        font-weight: 700;
        color: #f59e0b;
        margin-top: 0.4rem;
    }
    .rating-source {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: normal;
    }
    .rating-count-text {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 0.4rem;
    }
    .match-reason {
        font-size: 0.8rem;
        color: #10b981;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .footer-container {
        text-align: center;
        padding: 1.5rem 0;
        margin-top: 2rem;
        border-top: 1px solid #334155;
        color: #94a3b8;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Đang nạp catalog phim MovieLens 32M...")
def load_catalog(path: str, version: tuple[int, int]) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return df


@st.cache_data
def load_json(path: str, version: tuple[int, int] | None) -> dict:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def file_version(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


# Check catalog presence
if not CATALOG_PATH.exists():
    st.error("Chưa có movie catalog. Vui lòng chạy lệnh: `py scripts\\07_build_movie_catalog.py`")
    st.stop()

catalog_version = file_version(CATALOG_PATH)
catalog_df = load_catalog(str(CATALOG_PATH), catalog_version)
catalog_manifest = load_json(str(CATALOG_MANIFEST_PATH), file_version(CATALOG_MANIFEST_PATH))
als_manifest = load_json(str(ALS_MANIFEST_PATH), file_version(ALS_MANIFEST_PATH))
poster_loader = get_poster_loader()
tmdb_token = get_tmdb_token()
has_tmdb_token = bool(tmdb_token)


@st.fragment(run_every="1s")
def refresh_when_posters_ready(pending_ids: tuple[int, ...]) -> None:
    if poster_loader.any_completed(pending_ids, tmdb_token):
        st.rerun(scope="app")


# Detail Modal Dialog using Streamlit 1.51 @st.dialog
@st.dialog("🎬 Chi tiết phim", width="medium")
def show_movie_dialog(movie_data: dict[str, Any], tmdb_detail: TmdbMovieDetails | None) -> None:
    col_img, col_info = st.columns([1, 1.4])

    poster_src = (
        tmdb_detail.poster_url
        if (tmdb_detail and tmdb_detail.poster_url)
        else str(PLACEHOLDER_PATH)
    )

    with col_img:
        st.image(poster_src, width="stretch")
        if tmdb_detail and tmdb_detail.status == "ok" and tmdb_detail.web_url:
            st.markdown(f"[🔗 Xem trên TMDB]({tmdb_detail.web_url})", unsafe_allow_html=True)

    with col_info:
        title = movie_data.get("title", "")
        st.subheader(f"{title}")

        if tmdb_detail and tmdb_detail.title_vi and tmdb_detail.title_vi != title:
            st.caption(f"Tên tiếng Việt: **{tmdb_detail.title_vi}**")

        # Genres tags
        genres_vi = movie_data.get("all_genres_vi", [])
        matched_vi = set(movie_data.get("matched_genres_vi", []))
        tags_html = "".join(
            f'<span class="{"genre-tag-matched" if g in matched_vi else "genre-tag-neutral"}">{html.escape(g)}</span>'
            for g in genres_vi
        )
        st.markdown(tags_html, unsafe_allow_html=True)

        st.markdown("---")
        # MovieLens Rating
        avg_r = movie_data.get("avg_rating")
        count_r = movie_data.get("rating_count", 0)
        w_score = movie_data.get("weighted_score", 0.0)

        if pd.notna(avg_r):
            r_str = f"{avg_r:.2f}".replace(".", ",")
            st.markdown(f"★ **{r_str} / 5** <span class='rating-source'>· MovieLens 32M</span>", unsafe_allow_html=True)
        else:
            st.markdown("★ **Chưa có đánh giá** <span class='rating-source'>· MovieLens 32M</span>", unsafe_allow_html=True)
        st.caption(f"Tổng số đánh giá cộng đồng: **{count_r:,}** lượt".replace(",", "."))
        if pd.notna(w_score):
            st.caption(f"Điểm xếp hạng điều chỉnh (m=100): **{w_score:.3f}**")

        if tmdb_detail and tmdb_detail.vote_average:
            st.caption(f"Điểm TMDB: **{tmdb_detail.vote_average:.1f} / 10**")

    # Overview synopsis
    st.markdown("##### Nội dung phim")
    if tmdb_detail and tmdb_detail.overview:
        st.write(tmdb_detail.overview)
        if tmdb_detail.overview_lang == "en":
            st.caption("*(Mô tả tiếng Anh từ TMDB do chưa có bản dịch tiếng Việt)*")
    else:
        if not has_tmdb_token:
            st.info("Chưa cấu hình TMDB token. Thêm token vào `.streamlit/secrets.toml` để xem tóm tắt nội dung và poster đầy đủ.")
        elif pd.isna(movie_data.get("tmdbId")):
            st.info("Phim này chưa có mã liên kết TMDB.")
        elif tmdb_detail is None:
            st.info("Đang tải thông tin phim từ TMDB. Vui lòng đợi trong giây lát.")
        elif tmdb_detail.status in ("auth_error", "error"):
            st.info("TMDB hiện không trả về thông tin phim này. Vui lòng thử lại sau.")
        else:
            st.write("Chưa có mô tả nội dung cho bộ phim này.")


# --- HEADER ---
st.title("🎬 Hôm nay bạn muốn xem phim gì?")
st.subheader("Chọn thể loại bạn thích để khám phá phim phù hợp.")

# Build genre options for multiselect
# Example: "Hành động (Action)", "Khoa học viễn tưởng (Sci-Fi)"
genre_options = [f"{GENRE_MAP_EN_TO_VI[en]} ({en})" for en in ALL_GENRES_EN]

selected_options = st.multiselect(
    label="Thể loại yêu thích",
    options=genre_options,
    placeholder="Gõ để tìm kiếm thể loại (VD: Hành động, Hài, Sci-Fi...)",
    help="Hỗ trợ tìm kiếm bằng cả tiếng Việt và tiếng Anh.",
)
st.caption("Kết quả tự cập nhật khi chọn thể loại. Phim khớp ít nhất một thể loại; ưu tiên phim khớp nhiều thể loại.")

# Recompute all matches when the selected genres or catalog change.
selection_key = (catalog_version, tuple(selected_options))
if st.session_state.get("recommendation_key") != selection_key:
    st.session_state["recommendation_result"] = recommend_by_genres(
        catalog=catalog_df,
        selected_genres=selected_options,
    )
    st.session_state["recommendation_key"] = selection_key
    st.session_state["result_page"] = 1

res: RecommendationResult = st.session_state["recommendation_result"]

st.divider()

# --- RESULTS SECTION ---
st.subheader("Tất cả phim phù hợp với thể loại bạn chọn")

if not selected_options:
    st.info("👉 Chọn ít nhất một thể loại yêu thích ở trên để xem phim phù hợp.")
elif not res.has_results:
    st.warning("Không tìm thấy bộ phim nào phù hợp với các thể loại bạn đã chọn.")
else:
    total_pages = (res.total_matched + PAGE_SIZE - 1) // PAGE_SIZE
    if st.session_state.get("result_page", 1) > total_pages:
        st.session_state["result_page"] = 1
    summary_col, page_col = st.columns([3, 1], vertical_alignment="bottom")
    with page_col:
        page = st.number_input(
            f"Trang kết quả (1–{total_pages})",
            min_value=1,
            max_value=total_pages,
            step=1,
            key="result_page",
        )
    start = (page - 1) * PAGE_SIZE
    end = min(start + PAGE_SIZE, res.total_matched)
    with summary_col:
        st.markdown(f"**{res.total_matched:,} phim phù hợp**".replace(",", "."))
        st.caption(
            (
                f"Đang xem phim **{start + 1:,}–{end:,}**. "
                "Nhập số trang để xem toàn bộ danh sách."
            ).replace(",", ".")
        )

    # Only request posters for the visible page; the result itself has no movie limit.
    displayed_movies = res.movies.iloc[start:end].to_dict(orient="records")
    tmdb_ids = [m.get("tmdbId") for m in displayed_movies]
    imdb_by_tmdb = {
        int(movie["tmdbId"]): str(movie["imdbId"])
        for movie in displayed_movies
        if pd.notna(movie.get("tmdbId")) and pd.notna(movie.get("imdbId"))
    }
    tmdb_details_map, pending_ids = poster_loader.snapshot(
        tmdb_ids, tmdb_token, imdb_by_tmdb
    )
    pending_set = set(pending_ids)

    # 3 cards per row layout
    num_cols = 3
    for row_idx in range(0, len(displayed_movies), num_cols):
        row_movies = displayed_movies[row_idx : row_idx + num_cols]
        cols = st.columns(num_cols)

        for col_idx, movie in enumerate(row_movies):
            with cols[col_idx]:
                with st.container(border=True):
                    mid = movie["movieId"]
                    tid = movie.get("tmdbId")
                    detail = tmdb_details_map.get(int(tid)) if pd.notna(tid) else None

                    # Poster
                    if pd.notna(tid) and int(tid) in pending_set:
                        st.markdown(
                            '<div class="poster-loading"><span class="poster-loading-icon">🎞️</span>'
                            '<span>Đang tải poster...</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        poster_url = detail.poster_url if (detail and detail.poster_url) else str(PLACEHOLDER_PATH)
                        st.image(poster_url, width="stretch")

                    # Title & Year
                    title = html.escape(str(movie["title"]), quote=True)
                    st.markdown(
                        f'<div class="movie-card-title" title="{title}">{title}</div>',
                        unsafe_allow_html=True,
                    )

                    # Genres with matched highlighted
                    genres_vi = movie.get("all_genres_vi", [])
                    matched_vi = set(movie.get("matched_genres_vi", []))
                    tags_html = "".join(
                        f'<span class="{"genre-tag-matched" if g in matched_vi else "genre-tag-neutral"}">{html.escape(g)}</span>'
                        for g in genres_vi
                    )
                    st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)

                    # Rating score & Count
                    avg_r = movie.get("avg_rating")
                    rating_label = (
                        f"★ {avg_r:.1f}/5".replace(".", ",")
                        if pd.notna(avg_r)
                        else "★ Chưa có đánh giá"
                    )
                    st.markdown(
                        f"<div class='rating-badge'>{rating_label} <span class='rating-source'>· MovieLens</span></div>",
                        unsafe_allow_html=True,
                    )

                    count_r = movie.get("rating_count", 0)
                    formatted_count = f"{count_r:,}".replace(",", ".")
                    st.markdown(
                        f"<div class='rating-count-text'>{formatted_count} lượt đánh giá</div>",
                        unsafe_allow_html=True,
                    )

                    # Recommendation reason
                    st.markdown(
                        f"<div class='match-reason'>🎯 {html.escape(movie.get('reason', ''))}</div>",
                        unsafe_allow_html=True,
                    )

                    # Detail button
                    if st.button("Xem chi tiết", key=f"btn_detail_{mid}", width="stretch"):
                        show_movie_dialog(movie, detail)

    if pending_ids:
        refresh_when_posters_ready(tuple(pending_ids))

# --- SIDEBAR / RESEARCH METRICS SECTION ---
with st.sidebar:
    st.header("⚙️ Cấu hình & Trạng thái")
    tmdb_status = poster_loader.api_status(tmdb_token)
    if tmdb_status == "no_token":
        st.warning("⚠️ TMDB Token: Chưa cấu hình (Dùng ảnh placeholder)")
        st.caption("Xem hướng dẫn trong `.streamlit/secrets.toml.example` để kích hoạt tải ảnh TMDB.")
    elif tmdb_status == "connected":
        st.success("✅ TMDB API: Đã xác minh kết nối")
    elif tmdb_status == "auth_error":
        st.error("❌ TMDB từ chối token. Kiểm tra lại cấu hình.")
    elif tmdb_status == "unavailable":
        st.warning("⚠️ TMDB tạm thời không kết nối được. Đang dùng ảnh thay thế.")
    else:
        st.info("ℹ️ TMDB token đã cấu hình; chưa xác minh kết nối hiện tại.")

    st.markdown("---")
    st.header("📊 Thông tin đề tài")
    st.caption("Hệ thống gợi ý phim MovieLens 32M - Đề tài 15")

    # Catalog Stats
    with st.expander("📚 Dữ liệu Catalog", expanded=True):
        st.write(f"- **Tổng số phim:** {catalog_manifest.get('total_movies', len(catalog_df)):,}".replace(",", "."))
        st.write(f"- **Phim có đánh giá:** {catalog_manifest.get('movies_with_ratings', 0):,}".replace(",", "."))
        st.write(f"- **Ratings thống kê:** {catalog_manifest.get('total_ratings', 28709236):,}".replace(",", "."))
        st.write(f"- **Điểm TB toàn cục (C):** {catalog_manifest.get('global_avg_rating_C', 3.5463):.4f}")
        st.write(f"- **Hệ số điều chỉnh (m):** {catalog_manifest.get('m_regularization', 100.0)}")

    # ALS Model Research Metrics
    with st.expander("🤖 Mô hình ALS Spark (Nghiên cứu)"):
        test_m = als_manifest.get("test_rating_metrics", {})
        topk_m = als_manifest.get("test_topk_metrics", {})
        params = als_manifest.get("selected_params", {})

        st.markdown(
            f"""
            - **Thuật toán:** Spark MLlib ALS
            - **Tham số tối ưu:** rank={params.get('rank', 16)}, regParam={params.get('regParam', 0.08)}, maxIter={params.get('maxIter', 20)}
            - **Test RMSE:** `{test_m.get('rmse', 0):.4f}`
            - **Test MAE:** `{test_m.get('mae', 0):.4f}`
            - **Precision@10:** `{topk_m.get('precision_at_k', 0):.6f}`
            - **Recall@10:** `{topk_m.get('recall_at_k', 0):.6f}`
            """
        )
        st.caption("Gợi ý thể loại hiện tại áp dụng thuật toán lọc cộng đồng có điều chỉnh trọng số, độc lập với ALS User ID.")

# --- FOOTER ---
st.markdown(
    """
    <div class="footer-container">
        <div>Nguồn điểm: <strong>MovieLens 32M</strong> · Nguồn ảnh & mô tả: <strong>The Movie Database (TMDB)</strong></div>
        <div style="margin-top: 0.5rem; font-size: 0.78rem; color: #64748b;">
            This product uses the TMDB API but is not endorsed or certified by TMDB.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
