"""Convert each video's three scores, then average all valid videos per model."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
from statistics import mean

from calibration import aesthetic_100, official_technical_100, physics_100
from common import ROOT, identity

SCORE_FIELDS = ("technical_raw", "aes_v25_mean", "physics_raw",
                "technical_100", "aesthetic_100", "physics_100", "vq_100")


def read_latest(path: Path) -> dict[str, dict]:
    """Read the last result for each video and retain successful scores."""
    rows = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                rows[row["path"]] = row
    return {key: row for key, row in rows.items() if row["status"] == "ok"}


def join(technical: dict, aesthetic: dict, physics: dict) -> list[dict]:
    """Match the three components of each video and compute its VQ."""
    rows = []
    for key in sorted(technical.keys() & aesthetic.keys() & physics.keys()):
        raw_t = float(technical[key]["technical_raw"])
        raw_a = float(aesthetic[key]["aes_v25_mean"])
        raw_p = float(physics[key]["physics_raw"])
        t = official_technical_100(raw_t)
        a = aesthetic_100(raw_a)
        p = physics_100(raw_p)
        rows.append({**identity(key),
                     "technical_raw": raw_t, "aes_v25_mean": raw_a, "physics_raw": raw_p,
                     "technical_100": t, "aesthetic_100": a, "physics_100": p,
                     "vq_100": mean((t, a, p))})
    return rows


def summarize(rows: list[dict]) -> list[dict]:
    """Give every valid video equal weight in its model's mean."""
    groups = defaultdict(list)
    for row in rows:
        groups[row["model"]].append(row)
    return [{"model": model, "n": len(videos),
             **{field: mean(video[field] for video in videos) for field in SCORE_FIELDS}}
            for model, videos in sorted(groups.items())]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--technical", type=Path, default=ROOT / "results/technical.jsonl")
    parser.add_argument("--aesthetic", type=Path, default=ROOT / "results/aesthetic.jsonl")
    parser.add_argument("--physics", type=Path, default=ROOT / "results/physics.jsonl")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results/aggregate")
    args = parser.parse_args()
    rows = join(read_latest(args.technical), read_latest(args.aesthetic), read_latest(args.physics))
    if not rows:
        parser.error("No videos with three successful component scores")
    models = summarize(rows)
    write_csv(args.out_dir / "per_sample.csv", rows)
    write_csv(args.out_dir / "by_model.csv", models)
    print(f"Averaged {len(rows)} videos across {len(models)} models: {args.out_dir}")


if __name__ == "__main__":
    main()
