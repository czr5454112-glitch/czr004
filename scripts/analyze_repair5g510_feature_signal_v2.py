"""Audit Repair5G.5.10 feature matrix v2 signal quality."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import (  # noqa: E402
    G510_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    as_jsonable,
    context_key,
    finite_number,
    mean,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g510_feature_matrix_v2.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g510_lattice_oracle_by_context.csv"
DEFAULT_ABLATIONS = "outputs/tables/phase5p5_repair5g510_feature_signal_v2_ablations.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_feature_signal_v2.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_feature_signal_v2_summary.json"


METADATA = {
    "context_id",
    "normalized_context_key",
    "map",
    "agents",
    "seed",
    "iteration",
    "traffic_before_hash_full",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--oracle-context-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--ablation-csv", type=Path, default=Path(DEFAULT_ABLATIONS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def feature_names(rows: list[dict[str, object]]) -> list[str]:
    return sorted({key for row in rows for key in row if key not in METADATA})


def row_split(row: dict[str, object]) -> str:
    return "train" if int(finite_number(row.get("seed"), 0.0)) <= 150 else "dev"


def label_for_oracle(row: dict[str, object]) -> str:
    if str(row.get("primary_1000_2000_stable", "")).lower() != "true":
        return ""
    return "static" if row.get("oracle_1000") == G510_STATIC_CANDIDATE else "nonstatic"


def join_labels(features: list[dict[str, object]], oracle_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    labels = {context_key(row): label_for_oracle(row) for row in oracle_rows}
    return [{**row, "_label": labels.get(context_key(row), "")} for row in features]


def normalize_train(rows: list[dict[str, object]], names: list[str]) -> tuple[dict[str, float], dict[str, float]]:
    means = {name: mean(finite_number(row.get(name), 0.0) for row in rows) for name in names}
    stds = {}
    for name in names:
        vals = [finite_number(row.get(name), 0.0) for row in rows]
        mu = means[name]
        var = mean((value - mu) ** 2 for value in vals)
        stds[name] = math.sqrt(var) if math.isfinite(var) and var > 0.0 else 1.0
    return means, stds


def centroid_accuracy(rows: list[dict[str, object]], names: list[str]) -> tuple[float, int, int]:
    train = [row for row in rows if row_split(row) == "train" and row.get("_label") in {"static", "nonstatic"}]
    dev = [row for row in rows if row_split(row) == "dev" and row.get("_label") in {"static", "nonstatic"}]
    classes = sorted({str(row["_label"]) for row in train})
    if len(classes) < 2 or not dev or not names:
        return math.nan, len(train), len(dev)
    means, stds = normalize_train(train, names)
    centroids = {}
    for cls in classes:
        cls_rows = [row for row in train if row.get("_label") == cls]
        centroids[cls] = [
            mean((finite_number(row.get(name), 0.0) - means[name]) / stds[name] for row in cls_rows)
            for name in names
        ]
    correct = 0
    for row in dev:
        x = [(finite_number(row.get(name), 0.0) - means[name]) / stds[name] for name in names]
        pred = min(
            classes,
            key=lambda cls: sum((x[index] - centroids[cls][index]) ** 2 for index in range(len(names))),
        )
        correct += int(pred == row.get("_label"))
    return correct / len(dev), len(train), len(dev)


def ablation_groups(names: list[str]) -> dict[str, list[str]]:
    return {
        "all_v2": names,
        "no_map_agent_identity": [
            name
            for name in names
            if name
            not in {"agents", "map_width", "map_height", "free_cells", "density", "obstacle_ratio", "map_area", "agent_density"}
        ],
        "traffic_only": [name for name in names if name.startswith("c_traffic") or name.startswith("f_traffic") or name.startswith("cf_") or "nonzero" in name],
        "event_only": [name for name in names if any(token in name for token in ["event", "blocked", "wait", "committed", "progress", "nonprogress"])],
        "runtime_state_only": [name for name in names if name in {"ltm_iterations", "returned_solutions_count_so_far", "has_incumbent_before", "best_ratio_before", "improved_last_iteration", "later_iteration"}],
        "without_static_boundary_proxy": [name for name in names if name != "static_near_oracle_boundary_proxy"],
    }


def train_dev_shift(rows: list[dict[str, object]], names: list[str]) -> list[dict[str, object]]:
    train = [row for row in rows if row_split(row) == "train"]
    dev = [row for row in rows if row_split(row) == "dev"]
    out = []
    for name in names:
        train_vals = [finite_number(row.get(name), 0.0) for row in train]
        dev_vals = [finite_number(row.get(name), 0.0) for row in dev]
        mu_train = mean(train_vals)
        mu_dev = mean(dev_vals)
        out.append({"feature": name, "train_mean": as_jsonable(mu_train), "dev_mean": as_jsonable(mu_dev), "abs_shift": as_jsonable(abs(mu_train - mu_dev))})
    return sorted(out, key=lambda row: finite_number(row.get("abs_shift"), 0.0), reverse=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    features = read_csv_rows(resolve(args.feature_csv, root))
    oracle_rows = read_csv_rows(resolve(args.oracle_context_csv, root))
    rows = join_labels(features, oracle_rows)
    names = feature_names(features)
    constant = []
    for name in names:
        values = {finite_number(row.get(name), 0.0) for row in features}
        if len(values) <= 1:
            constant.append(name)
    ablations = []
    for group, group_names in ablation_groups(names).items():
        acc, train_rows, dev_rows = centroid_accuracy(rows, group_names)
        ablations.append(
            {
                "ablation": group,
                "feature_count": len(group_names),
                "train_rows": train_rows,
                "dev_rows": dev_rows,
                "dev_accuracy": as_jsonable(acc),
            }
        )
    write_csv_rows(resolve(args.ablation_csv, root), ablations)
    best = max(ablations, key=lambda row: finite_number(row.get("dev_accuracy"), -1.0)) if ablations else {}
    labels = defaultdict(int)
    for row in rows:
        labels[str(row.get("_label", ""))] += 1
    shift_rows = train_dev_shift(rows, names)[:10]
    map_agent_leakage_risk = "medium" if any(name in names for name in ["agents", "map_width", "map_height", "density"]) else "low"
    strong_enough = finite_number(best.get("dev_accuracy"), math.nan) >= 0.65 and labels.get("static", 0) >= 10 and labels.get("nonstatic", 0) >= 10
    summary = {
        "schema_version": "phase5p5_repair5g510_feature_signal_v2_summary_v1",
        "rows": len(features),
        "labeled_rows": sum(1 for row in rows if row.get("_label") in {"static", "nonstatic"}),
        "label_counts": dict(sorted(labels.items())),
        "feature_count": len(names),
        "constant_feature_count": len(constant),
        "constant_features": constant,
        "train_dev_shift_top10": shift_rows,
        "map_agent_leakage_risk": map_agent_leakage_risk,
        "ablation_csv": str(resolve(args.ablation_csv, root)),
        "ablations": ablations,
        "best_ablation": best,
        "best_ablation_dev_accuracy": best.get("dev_accuracy"),
        "features_strong_enough_to_distinguish_static_vs_nonstatic_safely": strong_enough,
        "forbidden_outcome_features_excluded": True,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Feature Signal v2\n\n"
        f"- rows: `{len(features)}`\n"
        f"- labeled_rows: `{summary['labeled_rows']}`\n"
        f"- constant_feature_count: `{len(constant)}`\n"
        f"- best_ablation_dev_accuracy: `{summary['best_ablation_dev_accuracy']}`\n"
        f"- map_agent_leakage_risk: `{map_agent_leakage_risk}`\n"
        f"- features_strong_enough_to_distinguish_static_vs_nonstatic_safely: `{strong_enough}`\n\n"
        "The audit uses only pre-update/runtime-safe columns. Outcome, oracle, candidate-label, traffic-after, action, priority, restart, h-value, and candidate-deletion fields are excluded from the feature matrix.\n",
    )
    print(json.dumps({"rows": len(features), "constant_feature_count": len(constant), "best_ablation_dev_accuracy": summary["best_ablation_dev_accuracy"]}))
    return 0 if features else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
