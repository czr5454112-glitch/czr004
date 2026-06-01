"""Create the Repair5E.5 cross-fold utility reranker runtime artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_RUNTIME = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_STATS_RUNTIME = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector"
DEFAULT_OUTPUT_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker"
DEFAULT_SHUFFLED_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic"
DEFAULT_LOOSE_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic"
DEFAULT_STRICT_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic"
DEFAULT_WIDE_CSV = "outputs/tables/phase5p5_repair5e5_crossfold_utility_wide.csv"
DEFAULT_UTILITY_SUMMARY = "outputs/reports/phase5p5_repair5e5_crossfold_utility_summary.json"
DEFAULT_THRESHOLD_SUMMARY = "outputs/reports/phase5p5_repair5e5_threshold_sweep_summary.json"
DEFAULT_SUPPORT_SUMMARY = "outputs/reports/phase5p5_repair5e5_crossfold_support_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e5_selector_artifact_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e5_selector_artifact_summary.json"

RUNTIME_FILES = [
    "features.txt",
    "mean.csv",
    "std.csv",
    "rules.csv",
    "layer0_weight.csv",
    "layer0_bias.csv",
    "rule_head_weight.csv",
    "rule_head_bias.csv",
    "safety_head_weight.csv",
    "safety_head_bias.csv",
    "delta_head_weight.csv",
    "delta_head_bias.csv",
    "laur_mlp_v1_weights.json",
    "laur_mlp_v1_rules.json",
    "laur_mlp_v1_feature_stats.json",
]

NONADDITIVE_RULES = [
    "block_heavy",
    "block_light",
    "commit_heavy",
    "decay_090",
    "decay_095",
    "wait_heavy",
    "wait_light",
]

SHUFFLED_RULE_MAP = {
    "block_heavy": "wait_light",
    "block_light": "decay_090",
    "commit_heavy": "wait_heavy",
    "decay_090": "block_light",
    "decay_095": "wait_heavy",
    "wait_heavy": "decay_095",
    "wait_light": "block_heavy",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def finite(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if out == out else default


def copy_runtime(source: Path, stats_runtime: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for name in RUNTIME_FILES:
        src = source / name
        if src.exists():
            shutil.copy2(src, output / name)
        else:
            missing.append(name)
    if missing:
        raise FileNotFoundError(f"missing runtime files: {missing}")
    for name in ["ood_feature_stats_train.csv", "ood_feature_stats_override.csv"]:
        src = stats_runtime / name
        if src.exists():
            shutil.copy2(src, output / name)


def threshold_variant(thresholds: dict[str, Any], kind: str) -> dict[str, Any]:
    out = dict(thresholds)
    out["rule_risk_caps"] = dict(thresholds.get("rule_risk_caps") or {})
    if kind == "loose":
        out["min_predicted_margin"] = max(0.0, float(out.get("min_predicted_margin", 0.001)) * 0.5)
        out["min_support_count"] = max(1, int(out.get("min_support_count", 4)) // 2)
        out["min_fold_agreement"] = max(1, int(out.get("min_fold_agreement", 1)) - 1)
        out["max_rule_risk"] = max(float(out.get("max_rule_risk", 0.1)), 0.25)
        out["non_additive_budget"] = max(int(out.get("non_additive_budget", 99)), 99)
    elif kind == "strict":
        out["min_predicted_margin"] = float(out.get("min_predicted_margin", 0.001)) * 2.0
        out["min_support_count"] = int(out.get("min_support_count", 4)) + 4
        out["min_fold_agreement"] = min(4, int(out.get("min_fold_agreement", 1)) + 1)
        out["max_rule_risk"] = min(float(out.get("max_rule_risk", 0.1)), 0.1)
        out["non_additive_budget"] = min(int(out.get("non_additive_budget", 99)), 1)
        out["allow_commit_heavy"] = False
    return out


def row_selected_rule(row: dict[str, str], thresholds: dict[str, Any]) -> str:
    rule = row.get("best_nonadditive_rule", "additive_ltm")
    if rule == "additive_ltm" or rule not in NONADDITIVE_RULES:
        return "additive_ltm"
    if rule == "commit_heavy" and not bool(thresholds.get("allow_commit_heavy", False)):
        return "additive_ltm"
    margin = finite(row.get("predicted_margin_ratio"), 0.0)
    support = finite(row.get(f"{rule}_support_instances"), 0.0)
    risk = finite(row.get(f"{rule}_false_positive_risk"), 1.0)
    agreement = finite(row.get(f"{rule}_fold_agreement"), 0.0)
    iteration = finite(row.get("iteration"), 0.0)
    risk_caps = thresholds.get("rule_risk_caps") or {}
    risk_cap = float(risk_caps.get(rule, thresholds.get("max_rule_risk", 0.1)))
    if margin < float(thresholds.get("min_predicted_margin", 0.001)):
        return "additive_ltm"
    if support < int(thresholds.get("min_support_count", 4)):
        return "additive_ltm"
    if risk > risk_cap:
        return "additive_ltm"
    if agreement < int(thresholds.get("min_fold_agreement", 1)):
        return "additive_ltm"
    if iteration > int(thresholds.get("non_additive_budget", 99)):
        return "additive_ltm"
    return rule


def selector_rows(
    utility_rows: list[dict[str, str]],
    *,
    fold_id: int,
    thresholds: dict[str, Any],
    source: str,
    shuffle_labels: bool = False,
) -> list[dict[str, Any]]:
    rows = [row for row in utility_rows if int(finite(row.get("fold_id"), -1)) == int(fold_id)]
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        rule = row_selected_rule(row, thresholds)
        if rule == "additive_ltm":
            continue
        key = (rule, row.get("runtime_feature_hash", ""), row.get("iteration", ""))
        if key in seen:
            continue
        seen.add(key)
        selected.append(
            {
                "rule_id": rule,
                "map_width": feature_value(row, "map_width"),
                "map_height": feature_value(row, "map_height"),
                "obstacle_ratio_min": max(0.0, feature_value(row, "obstacle_ratio") - 0.01),
                "obstacle_ratio_max": min(1.0, feature_value(row, "obstacle_ratio") + 0.01),
                "agents": finite(row.get("agents"), 0.0),
                "predicted_margin_ratio": finite(row.get("predicted_margin_ratio"), 0.0),
                "nearest_support_count": int(finite(row.get(f"{rule}_support_instances"), 0.0)),
                "min_support_neighbors": int(thresholds.get("min_support_count", 4)),
                "min_predicted_margin_ratio": float(thresholds.get("min_predicted_margin", 0.001)),
                "max_neighbor_distance": float(thresholds.get("max_neighbor_distance", 1.0e9)),
                "feature_values": row.get("feature_values", ""),
                "source": source,
                "map": row.get("map", ""),
                "instance_id": row.get("instance_id", ""),
                "iteration": row.get("iteration", ""),
                "fold_id": fold_id,
                "false_positive_risk": finite(row.get(f"{rule}_false_positive_risk"), 1.0),
                "fold_agreement": int(finite(row.get(f"{rule}_fold_agreement"), 0.0)),
            }
        )
    if shuffle_labels:
        for row in selected:
            row["rule_id"] = SHUFFLED_RULE_MAP.get(str(row["rule_id"]), "wait_light")
            row["source"] = "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic"
    return selected


def feature_value(row: dict[str, str], name: str) -> float:
    try:
        names = json.loads(row.get("runtime_feature_names", "[]"))
        values = json.loads(row.get("runtime_feature_values", "[]"))
    except json.JSONDecodeError:
        return 0.0
    if not isinstance(names, list) or not isinstance(values, list):
        return 0.0
    by_name = {str(feature): finite(value, 0.0) for feature, value in zip(names, values)}
    return by_name.get(name, 0.0)


def write_selector_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "rule_id",
        "map_width",
        "map_height",
        "obstacle_ratio_min",
        "obstacle_ratio_max",
        "agents",
        "predicted_margin_ratio",
        "nearest_support_count",
        "min_support_neighbors",
        "min_predicted_margin_ratio",
        "max_neighbor_distance",
        "feature_values",
        "source",
        "map",
        "instance_id",
        "iteration",
        "fold_id",
        "false_positive_risk",
        "fold_agreement",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_runtime(
    *,
    source_runtime: Path,
    stats_runtime: Path,
    output: Path,
    utility_rows: list[dict[str, str]],
    fold_id: int,
    thresholds: dict[str, Any],
    source: str,
    shuffle_labels: bool = False,
) -> dict[str, Any]:
    copy_runtime(source_runtime, stats_runtime, output)
    rows = selector_rows(
        utility_rows,
        fold_id=fold_id,
        thresholds=thresholds,
        source=source,
        shuffle_labels=shuffle_labels,
    )
    selector_csv = output / "repair5e4_utility_selector.csv"
    write_selector_csv(selector_csv, rows)
    manifest = {
        "schema_version": "phase5p5_repair5e5_runtime_variant_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_dir": str(output),
        "fold_id": fold_id,
        "selector_rows": len(rows),
        "selected_rule_distribution": dict(Counter(str(row["rule_id"]) for row in rows)),
        "thresholds": thresholds,
        "selector_csv_sha256": sha256_file(selector_csv),
    }
    (output / "repair5e5_crossfold_utility_reranker_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.5 Cross-Fold Utility Reranker Runtime\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- bounded_delta_updateparams: `false`\n")
        handle.write("- richer_ltm_representation: `false`\n")
        handle.write(f"- runtime_dir: `{summary['runtime_dir']}`\n")
        handle.write(f"- selector_rows: `{summary['main_manifest']['selector_rows']}`\n")
        handle.write(f"- selected_thresholds: `{summary['selected_thresholds']}`\n")
        handle.write(f"- utility_table_hash: `{summary['utility_table_hash']}`\n")
        handle.write(f"- threshold_sweep_hash: `{summary['threshold_sweep_hash']}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-runtime-dir", type=Path, default=Path(DEFAULT_SOURCE_RUNTIME))
    parser.add_argument("--stats-runtime-dir", type=Path, default=Path(DEFAULT_STATS_RUNTIME))
    parser.add_argument("--output-runtime-dir", type=Path, default=Path(DEFAULT_OUTPUT_RUNTIME))
    parser.add_argument("--shuffled-runtime-dir", type=Path, default=Path(DEFAULT_SHUFFLED_RUNTIME))
    parser.add_argument("--loose-runtime-dir", type=Path, default=Path(DEFAULT_LOOSE_RUNTIME))
    parser.add_argument("--strict-runtime-dir", type=Path, default=Path(DEFAULT_STRICT_RUNTIME))
    parser.add_argument("--utility-wide-csv", type=Path, default=Path(DEFAULT_WIDE_CSV))
    parser.add_argument("--utility-summary-json", type=Path, default=Path(DEFAULT_UTILITY_SUMMARY))
    parser.add_argument("--threshold-summary-json", type=Path, default=Path(DEFAULT_THRESHOLD_SUMMARY))
    parser.add_argument("--support-summary-json", type=Path, default=Path(DEFAULT_SUPPORT_SUMMARY))
    parser.add_argument("--main-fold-id", type=int, default=4)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source_runtime = resolve_path(args.source_runtime_dir, root)
    stats_runtime = resolve_path(args.stats_runtime_dir, root)
    output_runtime = resolve_path(args.output_runtime_dir, root)
    shuffled_runtime = resolve_path(args.shuffled_runtime_dir, root)
    loose_runtime = resolve_path(args.loose_runtime_dir, root)
    strict_runtime = resolve_path(args.strict_runtime_dir, root)
    utility_wide = resolve_path(args.utility_wide_csv, root)
    utility_summary_path = resolve_path(args.utility_summary_json, root)
    threshold_summary_path = resolve_path(args.threshold_summary_json, root)
    support_summary_path = resolve_path(args.support_summary_json, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)

    utility_rows = read_csv(utility_wide)
    utility_summary = read_json(utility_summary_path)
    threshold_summary = read_json(threshold_summary_path)
    support_summary = read_json(support_summary_path)
    thresholds = dict(threshold_summary.get("selected_thresholds") or {})
    thresholds.setdefault("max_neighbor_distance", 1.0e9)
    thresholds.setdefault("rule_risk_caps", {})
    thresholds.setdefault("allow_commit_heavy", False)

    main_manifest = write_runtime(
        source_runtime=source_runtime,
        stats_runtime=stats_runtime,
        output=output_runtime,
        utility_rows=utility_rows,
        fold_id=int(args.main_fold_id),
        thresholds=thresholds,
        source="repair5e5_crossfold_utility_reranker",
    )
    shuffled_manifest = write_runtime(
        source_runtime=source_runtime,
        stats_runtime=stats_runtime,
        output=shuffled_runtime,
        utility_rows=utility_rows,
        fold_id=int(args.main_fold_id),
        thresholds=thresholds,
        source="repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
        shuffle_labels=True,
    )
    loose_manifest = write_runtime(
        source_runtime=source_runtime,
        stats_runtime=stats_runtime,
        output=loose_runtime,
        utility_rows=utility_rows,
        fold_id=int(args.main_fold_id),
        thresholds=threshold_variant(thresholds, "loose"),
        source="repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic",
    )
    strict_manifest = write_runtime(
        source_runtime=source_runtime,
        stats_runtime=stats_runtime,
        output=strict_runtime,
        utility_rows=utility_rows,
        fold_id=int(args.main_fold_id),
        thresholds=threshold_variant(thresholds, "strict"),
        source="repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic",
    )

    fold_manifests: dict[str, Any] = {}
    for fold_id in range(5):
        fold_manifest = write_runtime(
            source_runtime=source_runtime,
            stats_runtime=stats_runtime,
            output=output_runtime / f"fold_{fold_id}",
            utility_rows=utility_rows,
            fold_id=fold_id,
            thresholds=thresholds,
            source="repair5e5_crossfold_utility_reranker",
        )
        fold_manifests[f"fold_{fold_id}"] = fold_manifest

    scripts = [
        "scripts/create_repair5e5_crossfold_support.py",
        "scripts/create_repair5e5_crossfold_utility_tables.py",
        "scripts/tune_repair5e5_utility_thresholds.py",
        "scripts/create_repair5e5_crossfold_utility_reranker_runtime.py",
        "scripts/run_phase5p5_laur_diagnostic_preflight_exec.py",
    ]
    summary = {
        "schema_version": "phase5p5_repair5e5_crossfold_utility_reranker_runtime_v1",
        "created_at": datetime.now().isoformat(),
        "candidate_name": "repair5e5_crossfold_utility_reranker",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "bounded_delta_updateparams": False,
        "richer_ltm_representation": False,
        "output_space": "existing_8_rules_plus_additive_defer",
        "git_head_sha": git_value(["rev-parse", "HEAD"], root),
        "git_branch": git_value(["branch", "--show-current"], root),
        "source_runtime_dir": rel(source_runtime, root),
        "stats_runtime_dir": rel(stats_runtime, root),
        "runtime_dir": rel(output_runtime, root),
        "selected_thresholds": thresholds,
        "fold_definitions": support_summary.get("fold_definitions"),
        "main_fold_id": int(args.main_fold_id),
        "train_support_logs": support_summary.get("folds", {}),
        "forbidden_eval_logs": [],
        "feature_stats_hash": sha256_file(output_runtime / "ood_feature_stats_train.csv"),
        "utility_table": rel(utility_wide, root),
        "utility_table_hash": sha256_file(utility_wide),
        "utility_summary": utility_summary,
        "utility_summary_hash": sha256_file(utility_summary_path),
        "threshold_sweep_summary": rel(threshold_summary_path, root),
        "threshold_sweep_hash": sha256_file(threshold_summary_path),
        "script_hashes": {script: sha256_file(root / script) for script in scripts},
        "source_runtime_hashes": {name: sha256_file(source_runtime / name) for name in RUNTIME_FILES},
        "main_manifest": main_manifest,
        "fold_manifests": fold_manifests,
        "shuffled_labels_diagnostic_manifest": shuffled_manifest,
        "loose_threshold_diagnostic_manifest": loose_manifest,
        "strict_threshold_diagnostic_manifest": strict_manifest,
        "notes": [
            "Deterministic cross-fold KNN/radius-neighbor utility reranker over calibrated runtime features.",
            "Unsupported, low-margin, high-risk, or low-support contexts defer to additive_ltm.",
            "Runtime CSV uses the existing repair5e4_utility_selector.csv bridge filename for C++ compatibility.",
        ],
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"runtime_dir": rel(output_runtime, root), "summary_json": rel(summary_json, root)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
