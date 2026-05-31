"""Create the Repair5E.3 split-trained guarded selector runtime artifact."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from create_repair5e2_guarded_selector_runtime import (  # noqa: E402
    RUNTIME_FILES,
    build_recovery_specs,
    read_jsonl,
    write_recovery_csv,
)
from create_repair5e3_runtime_feature_stats_from_train import (  # noqa: E402
    collect_stats,
    read_feature_names,
    read_jsonl as read_update_jsonl,
    write_csv,
)


DEFAULT_SOURCE = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_OUTPUT = "artifacts/models/laur_ltm/repair5e3_split_guarded_selector"
DEFAULT_TRAIN_RAW_JSONL = "outputs/logs/phase5p5_repair5e_caseb_preflight/phase5p5_repair5e_caseb_preflight.jsonl"
DEFAULT_TRAIN_UPDATE_JSONL = "outputs/logs/phase5p5_repair5e_caseb_preflight/phase5p5_repair5e_caseb_preflight_laur_updates.jsonl"
DEFAULT_E2_RUNTIME = "artifacts/models/laur_ltm/repair5e2_guarded_oracle_aligned_selector"
DEFAULT_SHUFFLED_OUTPUT = "artifacts/models/laur_ltm/repair5e3_e2_shuffled_support_diagnostic"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e3_split_selector_report.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5e3_split_selector_summary.json"

DEFAULT_MAPS = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
DEFAULT_AGENT_COUNTS = [50, 100]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def copy_runtime(source: Path, output: Path) -> None:
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


def filter_train_rows(rows: list[dict[str, Any]], train_instance_ids: set[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row.get("seed", 0) or 0) in train_instance_ids]


def create_train_feature_stats(runtime_dir: Path, train_update_jsonl: Path, root: Path) -> dict[str, Any]:
    rows = read_update_jsonl(train_update_jsonl)
    feature_names = read_feature_names(runtime_dir)
    stats = collect_stats(rows, feature_names, root)
    write_csv(runtime_dir / "ood_feature_stats_train.csv", stats, ["feature_name", "mean", "std", "rows"])
    write_csv(runtime_dir / "ood_feature_stats_override.csv", stats, ["feature_name", "mean", "std"])
    feature_stats = {
        "schema_version": "phase5p5_repair5e3_train_feature_stats_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "stat_source": "train_support_update_logs_only",
        "train_update_jsonl": str(train_update_jsonl),
        "row_count": len(rows),
        "feature_count": len(stats),
        "features": stats,
    }
    (runtime_dir / "laur_mlp_v1_feature_stats.json").write_text(
        json.dumps(feature_stats, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return feature_stats


def read_recovery_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_recovery_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "map_width",
        "map_height",
        "obstacle_ratio_min",
        "obstacle_ratio_max",
        "agents",
        "rule_id",
        "support_mean_delta",
        "support_rows",
        "source",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def create_shuffled_ablation(e2_runtime: Path, output: Path, root: Path) -> dict[str, Any] | None:
    source_csv = e2_runtime / "repair5e2_recovery_rules.csv"
    if not e2_runtime.exists() or not source_csv.exists():
        return None
    copy_runtime(e2_runtime, output)
    rows = read_recovery_csv(source_csv)
    rule_ids = [row.get("rule_id", "additive_ltm") for row in rows]
    if len(rule_ids) > 1:
        shifted = rule_ids[1:] + rule_ids[:1]
        for row, rule_id in zip(rows, shifted):
            row["rule_id"] = rule_id
            row["source"] = "repair5e3_e2_shuffled_support_diagnostic"
    write_recovery_csv_rows(output / "repair5e2_recovery_rules.csv", rows)
    manifest = {
        "schema_version": "phase5p5_repair5e3_e2_shuffled_support_diagnostic_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "source_runtime_dir": rel(e2_runtime, root),
        "runtime_dir": rel(output, root),
        "source_recovery_csv": rel(source_csv, root),
        "source_recovery_sha256": sha256_file(source_csv),
        "notes": [
            "Ablation only: E2 support rule ids are rotated across contexts.",
            "This artifact is not a learned selector and must not be promoted.",
        ],
    }
    (output / "repair5e3_shuffled_support_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.3 Split Guarded Selector\n\n")
        handle.write("- diagnostic-only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- output_space: `existing_8_rules_plus_additive_defer`\n\n")
        handle.write(f"- source runtime: `{summary['source_runtime_dir']}`\n")
        handle.write(f"- output runtime: `{summary['runtime_dir']}`\n")
        handle.write(f"- train support paths: `{summary['train_support_paths']}`\n")
        handle.write(f"- train instance ids: `{summary['train_instance_ids']}`\n")
        handle.write(f"- eval instance ids forbidden: `{summary['eval_instance_ids_forbidden']}`\n")
        handle.write(f"- OOD stat source: `{summary['ood_stat_source']}`\n\n")
        handle.write("## Recovery Rules\n\n")
        handle.write("| map | agents | rule | support | better/equal/worse | mean delta |\n")
        handle.write("|---|---:|---|---:|---:|---:|\n")
        for row in summary["recovery_rules"]:
            handle.write(
                f"| {row['map']} | {int(row['agents'])} | {row['rule_id']} | "
                f"{row['support_rows']} | "
                f"{row['support_better']}/{row['support_equal']}/{row['support_worse']} | "
                f"{row['support_mean_delta']} |\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-runtime-dir", type=Path, default=Path(DEFAULT_SOURCE))
    parser.add_argument("--output-runtime-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--train-raw-jsonl", type=Path, default=Path(DEFAULT_TRAIN_RAW_JSONL))
    parser.add_argument("--train-update-jsonl", type=Path, default=Path(DEFAULT_TRAIN_UPDATE_JSONL))
    parser.add_argument("--train-instance-ids", nargs="+", type=int, default=[1, 2, 3])
    parser.add_argument("--eval-instance-ids-forbidden", nargs="+", type=int, default=list(range(4, 14)))
    parser.add_argument("--maps", nargs="+", default=DEFAULT_MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=DEFAULT_AGENT_COUNTS)
    parser.add_argument("--e2-runtime-dir", type=Path, default=Path(DEFAULT_E2_RUNTIME))
    parser.add_argument("--shuffled-ablation-runtime-dir", type=Path, default=Path(DEFAULT_SHUFFLED_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source = resolve_path(args.source_runtime_dir, root)
    output = resolve_path(args.output_runtime_dir, root)
    train_raw = resolve_path(args.train_raw_jsonl, root)
    train_update = resolve_path(args.train_update_jsonl, root)
    e2_runtime = resolve_path(args.e2_runtime_dir, root)
    shuffled_output = resolve_path(args.shuffled_ablation_runtime_dir, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)

    if not source.exists():
        raise FileNotFoundError(source)
    if not train_raw.exists():
        raise FileNotFoundError(train_raw)
    copy_runtime(source, output)

    train_instance_ids = {int(value) for value in args.train_instance_ids}
    forbidden_eval_ids = {int(value) for value in args.eval_instance_ids_forbidden}
    if train_instance_ids & forbidden_eval_ids:
        raise ValueError("train_instance_ids overlap eval_instance_ids_forbidden")
    train_rows = filter_train_rows(read_jsonl(train_raw), train_instance_ids)
    specs = build_recovery_specs(root, train_rows)
    if not specs:
        raise RuntimeError("no train-only recovery specs could be derived")
    write_recovery_csv(output / "repair5e2_recovery_rules.csv", specs)
    write_recovery_csv(output / "repair5e3_recovery_rules.csv", specs)
    feature_stats = create_train_feature_stats(output, train_update, root)
    shuffled_manifest = create_shuffled_ablation(e2_runtime, shuffled_output, root)

    support_rule_distribution = dict(Counter(row["rule_id"] for row in specs))
    hashes = {
        "source_runtime_files": {
            name: sha256_file(source / name)
            for name in RUNTIME_FILES
            if (source / name).exists()
        },
        "train_raw_jsonl": sha256_file(train_raw),
        "train_update_jsonl": sha256_file(train_update),
        "recovery_csv": sha256_file(output / "repair5e2_recovery_rules.csv"),
        "ood_feature_stats_train_csv": sha256_file(output / "ood_feature_stats_train.csv"),
    }
    summary = {
        "schema_version": "phase5p5_repair5e3_split_guarded_selector_runtime_v1",
        "created_at": datetime.now().isoformat(),
        "candidate_name": "repair5e3_split_guarded_selector",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "bounded_delta_updateparams": False,
        "richer_ltm_representation": False,
        "output_space": "existing_8_rules_plus_additive_defer",
        "source_runtime_dir": rel(source, root),
        "runtime_dir": rel(output, root),
        "train_support_paths": [rel(train_raw, root), rel(train_update, root)],
        "eval_log_paths": [],
        "forbidden_eval_support_paths": [],
        "train_instance_ids": sorted(train_instance_ids),
        "eval_instance_ids_forbidden": sorted(forbidden_eval_ids),
        "maps": list(args.maps),
        "agent_counts": [int(value) for value in args.agent_counts],
        "support_rule_distribution": support_rule_distribution,
        "commit_heavy_cap_or_penalty": "commit_heavy excluded from train-only recovery table",
        "ood_stat_source": "train_support_update_logs_only",
        "ood_feature_stats": {
            "feature_count": feature_stats["feature_count"],
            "row_count": feature_stats["row_count"],
            "path": rel(output / "ood_feature_stats_train.csv", root),
        },
        "file_hashes": hashes,
        "recovery_rules": specs,
        "shuffled_support_ablation_runtime_dir": rel(shuffled_output, root),
        "shuffled_support_ablation_manifest": shuffled_manifest,
        "notes": [
            "Uses Repair5D distilled runtime as the base scorer.",
            "Keeps the OOD/defer guard and additive fallback.",
            "Learns/reranks only from train-support oracle/static rows.",
            "Does not read eval logs while creating this runtime artifact.",
        ],
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "repair5e3_split_guarded_selector_manifest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(report, summary)
    print(json.dumps({"runtime_dir": str(output), "summary_json": str(summary_json), "report": str(report)}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
