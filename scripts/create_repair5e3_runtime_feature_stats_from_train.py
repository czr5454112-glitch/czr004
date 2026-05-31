"""Create train-derived Repair5E.3 runtime feature/OOD stats."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from analyze_repair5e_caseb_transfer import MAP_PATHS, map_stats, reconstruct_feature_values  # noqa: E402


DEFAULT_TRAIN_UPDATE_JSONL = "outputs/logs/phase5p5_repair5e_caseb_preflight/phase5p5_repair5e_caseb_preflight_laur_updates.jsonl"
DEFAULT_RUNTIME_DIR = "artifacts/models/laur_ltm/repair5e3_split_guarded_selector"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_feature_names(runtime_dir: Path) -> list[str]:
    path = runtime_dir / "features.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def row_features(row: dict[str, Any]) -> dict[str, float]:
    names = row.get("runtime_feature_names")
    values = row.get("runtime_feature_values")
    if not isinstance(names, list) or not isinstance(values, list):
        return {}
    return {str(name): finite(value, 0.0) for name, value in zip(names, values)}


def collect_stats(rows: list[dict[str, Any]], feature_names: list[str], root: Path | None = None) -> list[dict[str, Any]]:
    values_by_feature: dict[str, list[float]] = defaultdict(list)
    selected_names = set(feature_names)
    map_cache = {name: map_stats(root, name) for name in MAP_PATHS} if root is not None else {}
    for row in rows:
        features = row_features(row)
        if not features and root is not None and feature_names:
            values, _imputed = reconstruct_feature_values(
                row,
                map_cache.get(str(row.get("map")), {}),
                feature_names,
            )
            features = {name: finite(value, 0.0) for name, value in zip(feature_names, values)}
        for name, value in features.items():
            if selected_names and name not in selected_names:
                continue
            if math.isfinite(value):
                values_by_feature[name].append(value)

    out: list[dict[str, Any]] = []
    for name in feature_names or sorted(values_by_feature):
        values = values_by_feature.get(name, [])
        if values:
            mean = statistics.mean(values)
            stdev = statistics.pstdev(values) if len(values) > 1 else 1.0
            if abs(stdev) <= 1.0e-12:
                stdev = 1.0
        else:
            mean = 0.0
            stdev = 1.0
        out.append({"feature_name": name, "mean": mean, "std": stdev, "rows": len(values)})
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-update-jsonl", type=Path, action="append", default=[Path(DEFAULT_TRAIN_UPDATE_JSONL)])
    parser.add_argument("--runtime-dir", type=Path, default=Path(DEFAULT_RUNTIME_DIR))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    runtime_dir = resolve_path(args.runtime_dir, root)
    train_paths = [resolve_path(path, root) for path in args.train_update_jsonl]
    rows: list[dict[str, Any]] = []
    for path in train_paths:
        rows.extend(read_jsonl(path))
    feature_names = read_feature_names(runtime_dir)
    stats = collect_stats(rows, feature_names, root)

    runtime_dir.mkdir(parents=True, exist_ok=True)
    write_csv(runtime_dir / "ood_feature_stats_train.csv", stats, ["feature_name", "mean", "std", "rows"])
    write_csv(runtime_dir / "ood_feature_stats_override.csv", stats, ["feature_name", "mean", "std"])
    feature_stats = {
        "schema_version": "phase5p5_repair5e3_train_feature_stats_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "stat_source": "train_support_update_logs_only",
        "train_update_jsonl": [str(path) for path in train_paths],
        "feature_count": len(stats),
        "row_count": len(rows),
        "features": stats,
    }
    (runtime_dir / "laur_mlp_v1_feature_stats.json").write_text(
        json.dumps(feature_stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "runtime_dir": str(runtime_dir),
                "train_rows": len(rows),
                "feature_count": len(stats),
                "ood_feature_stats_train_csv": str(runtime_dir / "ood_feature_stats_train.csv"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
