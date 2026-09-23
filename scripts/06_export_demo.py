from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root / "src"))
from recommender.config import resolve_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare bounded recommendation files for the Streamlit demo.")
    parser.add_argument("--model-dir", default="models/als_final")
    parser.add_argument("--output-dir", default="artifacts/demo")
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = resolve_path(args.model_dir)
    output_dir = resolve_path(args.output_dir)
    source = source_dir / "recommendations" / "recommendations.parquet"
    if not source.exists():
        raise FileNotFoundError(f"Missing recommendation artifact: {source}")
    recommendations = pd.read_parquet(source)
    recommendations = recommendations[recommendations["rank"] <= args.top_k].copy()
    recommendations = recommendations.sort_values(["userId", "rank", "movieId"])
    output_dir.mkdir(parents=True, exist_ok=True)
    recommendations.to_parquet(output_dir / "recommendations.parquet", index=False)
    recommendations.to_csv(output_dir / "recommendations.csv", index=False, encoding="utf-8-sig")

    metrics_path = source_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_model_dir": str(source_dir),
        "recommendation_rows": int(len(recommendations)),
        "demo_users": int(recommendations["userId"].nunique()),
        "top_k": args.top_k,
        "selected_params": metrics.get("selected_params", {}),
        "test_rating_metrics": metrics.get("test_rating_metrics", {}),
        "test_topk_metrics": metrics.get("test_topk_metrics", {}),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"OK: demo recommendations written to {output_dir} ({len(recommendations):,} rows)")
    print(f"OK: manifest written to {output_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
