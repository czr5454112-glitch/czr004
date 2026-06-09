"""Create the Repair5E.4 closed-loop utility selector runtime artifact."""

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
DEFAULT_OUTPUT_RUNTIME = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector"
DEFAULT_SHUFFLED_RUNTIME = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic"
DEFAULT_E3_RUNTIME = "artifacts/models/laur_ltm/repair5e3_split_guarded_selector"
DEFAULT_E3_CALIBRATED_RUNTIME = "artifacts/models/laur_ltm/repair5e4_calibrated_guard_only_on_e3_split"
DEFAULT_UTILITY_TABLE = "outputs/tables/phase5p5_repair5e4_closed_loop_rule_utility_train.csv"
DEFAULT_UTILITY_SUMMARY = "outputs/reports/phase5p5_repair5e4_closed_loop_rule_utility_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e4_selector_artifact_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e4_selector_artifact_summary.json"

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


def copy_runtime(source: Path, output: Path) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for name in RUNTIME_FILES:
        src = source / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy2(src, output / name)
    if missing:
        raise FileNotFoundError(f"missing runtime files: {missing}")
    return missing


def copy_calibrated_stats(stats_runtime: Path, output: Path) -> dict[str, str | None]:
    copied: dict[str, str | None] = {}
    for name in ["ood_feature_stats_train.csv", "ood_feature_stats_override.csv"]:
        src = stats_runtime / name
        if src.exists():
            shutil.copy2(src, output / name)
            copied[name] = sha256_file(output / name)
        else:
            copied[name] = None
    return copied


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


def runtime_feature_map(row: dict[str, str]) -> dict[str, float]:
    try:
        names = json.loads(row.get("runtime_feature_names", "[]"))
        values = json.loads(row.get("runtime_feature_values", "[]"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(names, list) or not isinstance(values, list):
        return {}
    return {str(name): finite(value, 0.0) for name, value in zip(names, values)}


def selector_rows(
    utility_rows: list[dict[str, str]],
    *,
    min_support_neighbors: int,
    min_predicted_margin_ratio: float,
    max_commit_heavy_share: float,
) -> list[dict[str, Any]]:
    label_counts = Counter(row.get("label_rule", "additive_ltm") for row in utility_rows)
    positive_total = sum(count for rule, count in label_counts.items() if rule != "additive_ltm")
    commit_share = label_counts.get("commit_heavy", 0) / max(1, positive_total)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in utility_rows:
        rule = row.get("label_rule", "additive_ltm")
        if rule == "additive_ltm":
            continue
        margin = finite(row.get("positive_margin_ratio"), 0.0)
        support = int(finite(row.get(f"{rule}_group_support_instances"), 0.0))
        if support < min_support_neighbors or margin < min_predicted_margin_ratio:
            continue
        if rule == "commit_heavy" and (
            commit_share > max_commit_heavy_share
            or support < max(min_support_neighbors * 2, 3)
            or margin < 2.0 * min_predicted_margin_ratio
        ):
            continue
        feature_values = row.get("feature_values", "")
        if not feature_values:
            continue
        key = (rule, row.get("runtime_feature_hash", ""))
        if key in seen:
            continue
        seen.add(key)
        features = runtime_feature_map(row)
        obstacle = features.get("obstacle_ratio", 0.0)
        out.append(
            {
                "rule_id": rule,
                "map_width": features.get("map_width", 0.0),
                "map_height": features.get("map_height", 0.0),
                "obstacle_ratio_min": max(0.0, obstacle - 0.01),
                "obstacle_ratio_max": min(1.0, obstacle + 0.01),
                "agents": finite(row.get("agents"), 0.0),
                "predicted_margin_ratio": margin,
                "nearest_support_count": support,
                "min_support_neighbors": min_support_neighbors,
                "min_predicted_margin_ratio": min_predicted_margin_ratio,
                "feature_values": feature_values,
                "source": "closed_loop_rule_utility_train",
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "instance_id": row.get("instance_id", ""),
                "iteration": row.get("iteration", ""),
            }
        )
    return out


def write_selector_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        "feature_values",
        "source",
        "map",
        "instance_id",
        "iteration",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create_shuffled_runtime(source_runtime: Path, output: Path, selector_rows_in: list[dict[str, Any]]) -> dict[str, Any]:
    copy_runtime(source_runtime, output)
    copy_calibrated_stats(source_runtime, output)
    rows = [dict(row) for row in selector_rows_in]
    labels = [str(row["rule_id"]) for row in rows]
    if len(labels) > 1:
        shifted = labels[1:] + labels[:1]
        for row, label in zip(rows, shifted):
            row["rule_id"] = label
            row["source"] = "repair5e4_shuffled_labels_diagnostic"
    write_selector_csv(output / "repair5e4_utility_selector.csv", rows)
    manifest = {
        "schema_version": "phase5p5_repair5e4_shuffled_labels_runtime_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_dir": str(output),
        "selector_rows": len(rows),
        "notes": ["Ablation only: selector labels are rotated across support rows."],
    }
    (output / "repair5e4_shuffled_labels_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def create_calibrated_e3_runtime(e3_runtime: Path, stats_runtime: Path, output: Path) -> dict[str, Any] | None:
    if not e3_runtime.exists():
        return None
    copy_runtime(e3_runtime, output)
    for optional in ["repair5e2_recovery_rules.csv", "repair5e3_recovery_rules.csv"]:
        src = e3_runtime / optional
        if src.exists():
            shutil.copy2(src, output / optional)
    hashes = copy_calibrated_stats(stats_runtime, output)
    manifest = {
        "schema_version": "phase5p5_repair5e4_calibrated_guard_only_on_e3_split_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "source_runtime_dir": str(e3_runtime),
        "runtime_dir": str(output),
        "calibrated_stats_hashes": hashes,
        "notes": ["Ablation: keep E3 split selector support table, replace only OOD stats with E4 train-support calibration."],
    }
    (output / "repair5e4_calibrated_guard_only_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.4 Closed-Loop Utility Selector Runtime\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- output_space: `existing_8_rules_plus_additive_defer`\n")
        handle.write(f"- runtime_dir: `{summary['runtime_dir']}`\n")
        handle.write(f"- selector_rows: `{summary['selector_rows']}`\n")
        handle.write(f"- rule_distribution: `{summary['selector_rule_distribution']}`\n")
        handle.write(f"- feature_stats_sha256: `{summary['feature_stats_sha256']}`\n")
        handle.write(f"- closed_loop_utility_table_sha256: `{summary['closed_loop_utility_table_sha256']}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-runtime-dir", type=Path, default=Path(DEFAULT_SOURCE_RUNTIME))
    parser.add_argument("--output-runtime-dir", type=Path, default=Path(DEFAULT_OUTPUT_RUNTIME))
    parser.add_argument("--shuffled-runtime-dir", type=Path, default=Path(DEFAULT_SHUFFLED_RUNTIME))
    parser.add_argument("--e3-runtime-dir", type=Path, default=Path(DEFAULT_E3_RUNTIME))
    parser.add_argument("--calibrated-e3-runtime-dir", type=Path, default=Path(DEFAULT_E3_CALIBRATED_RUNTIME))
    parser.add_argument("--utility-table-csv", type=Path, default=Path(DEFAULT_UTILITY_TABLE))
    parser.add_argument("--utility-summary-json", type=Path, default=Path(DEFAULT_UTILITY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--train-instance-ids", nargs="+", type=int, default=list(range(1, 11)))
    parser.add_argument("--eval-instance-ids-forbidden", nargs="+", type=int, default=list(range(21, 41)))
    parser.add_argument("--min-support-neighbors", type=int, default=5)
    parser.add_argument("--min-predicted-margin-ratio", type=float, default=0.001)
    parser.add_argument("--max-commit-heavy-share", type=float, default=0.2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source = resolve_path(args.source_runtime_dir, root)
    output = resolve_path(args.output_runtime_dir, root)
    shuffled = resolve_path(args.shuffled_runtime_dir, root)
    e3_runtime = resolve_path(args.e3_runtime_dir, root)
    calibrated_e3 = resolve_path(args.calibrated_e3_runtime_dir, root)
    utility_table = resolve_path(args.utility_table_csv, root)
    utility_summary_path = resolve_path(args.utility_summary_json, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)

    copy_runtime(source, output)
    utility_rows = read_csv(utility_table)
    utility_summary = read_json(utility_summary_path)
    train_support_paths = []
    inputs = utility_summary.get("inputs", {}) if utility_summary else {}
    if isinstance(inputs, dict):
        for key in ("raw_jsonl", "update_jsonl"):
            value = inputs.get(key)
            if isinstance(value, list):
                train_support_paths.extend(str(item) for item in value)
    rows = selector_rows(
        utility_rows,
        min_support_neighbors=int(args.min_support_neighbors),
        min_predicted_margin_ratio=float(args.min_predicted_margin_ratio),
        max_commit_heavy_share=float(args.max_commit_heavy_share),
    )
    selector_csv = output / "repair5e4_utility_selector.csv"
    write_selector_csv(selector_csv, rows)
    shuffled_manifest = create_shuffled_runtime(output, shuffled, rows)
    calibrated_e3_manifest = create_calibrated_e3_runtime(e3_runtime, output, calibrated_e3)

    stats_csv = output / "ood_feature_stats_train.csv"
    train_ids = sorted(int(value) for value in args.train_instance_ids)
    forbidden_eval_ids = sorted(int(value) for value in args.eval_instance_ids_forbidden)
    if set(train_ids) & set(forbidden_eval_ids):
        raise ValueError("train_instance_ids overlap eval_instance_ids_forbidden")

    summary = {
        "schema_version": "phase5p5_repair5e4_closed_loop_utility_selector_runtime_v1",
        "created_at": datetime.now().isoformat(),
        "candidate_name": "repair5e4_closed_loop_utility_selector",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "bounded_delta_updateparams": False,
        "richer_ltm_representation": False,
        "output_space": "existing_8_rules_plus_additive_defer",
        "git_head_sha": git_value(["rev-parse", "HEAD"], root),
        "git_branch": git_value(["branch", "--show-current"], root),
        "source_runtime_dir": rel(source, root),
        "runtime_dir": rel(output, root),
        "selector_csv": rel(selector_csv, root),
        "selector_rows": len(rows),
        "selector_rule_distribution": dict(Counter(row["rule_id"] for row in rows)),
        "min_support_neighbors": int(args.min_support_neighbors),
        "min_predicted_margin_ratio": float(args.min_predicted_margin_ratio),
        "max_commit_heavy_share": float(args.max_commit_heavy_share),
        "train_instance_ids": train_ids,
        "eval_instance_ids_forbidden": forbidden_eval_ids,
        "train_support_paths": train_support_paths,
        "eval_log_paths": [],
        "closed_loop_utility_table": rel(utility_table, root),
        "closed_loop_utility_table_sha256": sha256_file(utility_table),
        "feature_stats_sha256": sha256_file(stats_csv),
        "source_runtime_hashes": {name: sha256_file(source / name) for name in RUNTIME_FILES if (source / name).exists()},
        "shuffled_labels_diagnostic_runtime_dir": rel(shuffled, root),
        "shuffled_labels_diagnostic_manifest": shuffled_manifest,
        "calibrated_guard_only_on_e3_split_runtime_dir": rel(calibrated_e3, root),
        "calibrated_guard_only_on_e3_split_manifest": calibrated_e3_manifest,
        "notes": [
            "Deterministic feature-space nearest-neighbor reranker from closed-loop utility labels.",
            "Unsupported, low-margin, or low-support contexts defer to additive_ltm.",
            "No eval logs are consumed while creating this runtime artifact.",
        ],
    }
    manifest = output / "repair5e4_closed_loop_utility_selector_manifest.json"
    manifest.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary["runtime_manifest"] = rel(manifest, root)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"runtime_dir": rel(output, root), "summary_json": rel(summary_json, root), "report": rel(report, root)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
