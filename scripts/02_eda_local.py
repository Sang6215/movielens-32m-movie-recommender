from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pyarrow.dataset as ds

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from recommender.config import resolve_path
from recommender.local_io import ensure_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create local EDA tables and charts for MovieLens 32M.")
    parser.add_argument("--parquet-dir", default="data/processed/parquet", help="Parquet input folder.")
    parser.add_argument("--report-dir", default="reports", help="Report output folder.")
    return parser.parse_args()


def scan_ratings(ratings_path: Path) -> tuple[dict[str, object], pd.Series, pd.Series]:
    dataset = ds.dataset(ratings_path, format="parquet")
    users: set[int] = set()
    movies: set[int] = set()
    rating_counts: Counter[float] = Counter()
    year_counts: Counter[int] = Counter()
    min_ts: int | None = None
    max_ts: int | None = None
    total_rows = 0

    scanner = dataset.scanner(columns=["userId", "movieId", "rating", "timestamp"], batch_size=1_000_000)
    for batch in scanner.to_batches():
        frame = batch.to_pandas()
        total_rows += len(frame)
        users.update(frame["userId"].unique().tolist())
        movies.update(frame["movieId"].unique().tolist())
        rating_counts.update(frame["rating"].value_counts().to_dict())
        years = pd.to_datetime(frame["timestamp"], unit="s").dt.year
        year_counts.update(years.value_counts().to_dict())
        batch_min = int(frame["timestamp"].min())
        batch_max = int(frame["timestamp"].max())
        min_ts = batch_min if min_ts is None else min(min_ts, batch_min)
        max_ts = batch_max if max_ts is None else max(max_ts, batch_max)

    summary = {
        "ratings": total_rows,
        "unique_users": len(users),
        "unique_rated_movies": len(movies),
        "min_rating_time": pd.to_datetime(min_ts, unit="s") if min_ts is not None else None,
        "max_rating_time": pd.to_datetime(max_ts, unit="s") if max_ts is not None else None,
    }

    rating_series = pd.Series(rating_counts, name="count").sort_index()
    year_series = pd.Series(year_counts, name="count").sort_index()
    return summary, rating_series, year_series


def analyze_genres(movies_path: Path) -> pd.Series:
    movies = pd.read_parquet(movies_path)
    counter: Counter[str] = Counter()
    for raw_genres in movies["genres"].fillna("(no genres listed)"):
        for genre in str(raw_genres).split("|"):
            counter[genre] += 1
    return pd.Series(counter, name="movie_count").sort_values(ascending=False)


def save_bar(series: pd.Series, path: Path, title: str, xlabel: str, ylabel: str) -> None:
    plt.figure(figsize=(10, 5))
    series.plot(kind="bar")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def series_to_markdown(series: pd.Series, index_name: str, value_name: str) -> str:
    lines = [f"| {index_name} | {value_name} |", "| --- | ---: |"]
    for index, value in series.items():
        if isinstance(value, float):
            rendered_value = f"{value:,.0f}" if value.is_integer() else f"{value:,.4f}"
        else:
            rendered_value = f"{int(value):,}"
        lines.append(f"| {index} | {rendered_value} |")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    parquet_dir = resolve_path(args.parquet_dir)
    report_dir = resolve_path(args.report_dir)
    table_dir = ensure_dir(report_dir / "tables")
    figure_dir = ensure_dir(report_dir / "figures")

    summary, rating_counts, year_counts = scan_ratings(parquet_dir / "ratings.parquet")
    genre_counts = analyze_genres(parquet_dir / "movies.parquet")

    pd.DataFrame([summary]).to_csv(table_dir / "eda_summary.csv", index=False)
    rating_counts.to_csv(table_dir / "rating_distribution.csv", header=True)
    year_counts.to_csv(table_dir / "ratings_by_year.csv", header=True)
    genre_counts.to_csv(table_dir / "genre_distribution.csv", header=True)

    summary_md = [
        "# EDA Summary",
        "",
        f"- Ratings: {summary['ratings']:,}",
        f"- Unique users: {summary['unique_users']:,}",
        f"- Unique rated movies: {summary['unique_rated_movies']:,}",
        f"- Rating time range: {summary['min_rating_time']} to {summary['max_rating_time']}",
        "",
        "## Rating Distribution",
        "",
        series_to_markdown(rating_counts, "rating", "count"),
        "",
        "## Top Genres",
        "",
        series_to_markdown(genre_counts.head(20), "genre", "movie_count"),
        "",
    ]
    (table_dir / "eda_summary.md").write_text("\n".join(summary_md), encoding="utf-8")

    save_bar(rating_counts, figure_dir / "rating_distribution.png", "Rating distribution", "Rating", "Count")
    save_bar(year_counts, figure_dir / "ratings_by_year.png", "Ratings by year", "Year", "Count")
    save_bar(genre_counts.head(20), figure_dir / "top_genres.png", "Top movie genres", "Genre", "Movie count")

    print(f"OK: EDA tables written to {table_dir}")
    print(f"OK: EDA figures written to {figure_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
