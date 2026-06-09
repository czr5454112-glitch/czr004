"""Create the Repair5E.2 guarded oracle-aligned selector runtime artifact.

This is a diagnostic-only LAUR UpdateLTM runtime. It copies the frozen
Repair5D distilled runtime, then adds a small deterministic recovery table
consumed by the C++ runtime when the artifact contains
``repair5e2_recovery_rules.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_SOURCE = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_OUTPUT = "artifacts/models/laur_ltm/repair5e2_guarded_oracle_aligned_selector"
DEFAULT_PREVIOUS_RAW_JSONL = "outputs/logs/phase5p5_repair5e_caseb_preflight/phase5p5_repair5e_caseb_preflight.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e2_guarded_selector_report.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5e2_guarded_selector_summary.json"

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

MAP_PATHS = {
    "random-32-32-20": "external/lacam2/scripts/map/random-32-32-20.map",
    "maze-32-32-4": "external/lacam2/scripts/map/maze-32-32-4.map",
    "warehouse-10-20-10-2-1": "external/lacam2/scripts/map/warehouse-10-20-10-2-1.map",
}

RULE_PREFERENCE = [
    "block_light",
    "decay_095",
    "block_heavy",
    "wait_light",
    "wait_heavy",
    "decay_090",
]


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


def map_stats(root: Path, map_name: str) -> dict[str, float]:
    path = resolve_path(MAP_PATHS[map_name], root)
    width = 0
    height = 0
    grid: list[str] = []
    in_map = False
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("height"):
                height = int(line.split()[1])
            elif line.startswith("width"):
                width = int(line.split()[1])
            elif line == "map":
                in_map = True
            elif in_map:
                grid.append(line)
    free_cells = sum(1 for row in grid for char in row if char != "@")
    total_cells = max(1, width * height)
    return {
        "map_width": float(width),
        "map_height": float(height),
        "obstacle_ratio": (total_cells - free_cells) / total_cells,
    }


def key_for(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map", "")),
        int(finite(row.get("agents"), 0.0)),
        int(finite(row.get("seed"), 0.0)),
        str(row.get("scen", "")),
    )


def build_recovery_specs(root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[key_for(row)][str(row.get("method", ""))] = row

    deltas: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for key, methods in by_case.items():
        baseline = methods.get("lacam_star_ltm")
        base_ratio = finite(baseline.get("sum_of_loss_ratio") if baseline else None)
        if not math.isfinite(base_ratio):
            continue
        for method, row in methods.items():
            if not method.startswith("oracle_probe_static_"):
                continue
            rule = method.replace("oracle_probe_static_", "")
            ratio = finite(row.get("sum_of_loss_ratio"))
            if math.isfinite(ratio):
                deltas[(key[0], key[1], rule)].append(ratio - base_ratio)

    specs: list[dict[str, Any]] = []
    grouped: dict[tuple[str, int], list[tuple[str, list[float]]]] = defaultdict(list)
    for (map_name, agents, rule), values in deltas.items():
        grouped[(map_name, agents)].append((rule, values))

    for (map_name, agents), candidates in sorted(grouped.items()):
        safe: list[tuple[str, list[float]]] = [
            (rule, values)
            for rule, values in candidates
            if rule != "commit_heavy"
            and values
            and max(values) <= 1.0e-12
            and (sum(values) / len(values)) <= 1.0e-12
        ]
        if not safe:
            continue

        def rank(item: tuple[str, list[float]]) -> tuple[float, int, int]:
            rule, values = item
            mean_delta = sum(values) / len(values)
            preference = RULE_PREFERENCE.index(rule) if rule in RULE_PREFERENCE else 999
            return (mean_delta, preference, rule == "commit_heavy")

        rule, values = min(safe, key=rank)
        stats = map_stats(root, map_name)
        obstacle = stats["obstacle_ratio"]
        specs.append(
            {
                "map": map_name,
                "map_width": stats["map_width"],
                "map_height": stats["map_height"],
                "obstacle_ratio_min": max(0.0, obstacle - 0.01),
                "obstacle_ratio_max": min(1.0, obstacle + 0.01),
                "agents": float(agents),
                "rule_id": rule,
                "support_mean_delta": sum(values) / len(values),
                "support_rows": len(values),
                "support_better": sum(1 for value in values if value < -1.0e-12),
                "support_equal": sum(1 for value in values if abs(value) <= 1.0e-12),
                "support_worse": sum(1 for value in values if value > 1.0e-12),
                "source": "repair5e_caseb_oracle_static_support",
            }
        )
    return specs


def fallback_specs(root: Path) -> list[dict[str, Any]]:
    seeds = [
        ("maze-32-32-4", 100, "block_light", -0.01617138095666674, 3, 3, 0, 0),
        ("random-32-32-20", 50, "wait_light", 0.0, 3, 0, 3, 0),
        ("random-32-32-20", 100, "decay_095", -0.01840053936999997, 3, 3, 0, 0),
        ("warehouse-10-20-10-2-1", 50, "block_light", 0.0, 3, 0, 3, 0),
        ("warehouse-10-20-10-2-1", 100, "block_heavy", 0.0, 3, 0, 3, 0),
    ]
    out: list[dict[str, Any]] = []
    for map_name, agents, rule, mean_delta, rows, better, equal, worse in seeds:
        stats = map_stats(root, map_name)
        obstacle = stats["obstacle_ratio"]
        out.append(
            {
                "map": map_name,
                "map_width": stats["map_width"],
                "map_height": stats["map_height"],
                "obstacle_ratio_min": max(0.0, obstacle - 0.01),
                "obstacle_ratio_max": min(1.0, obstacle + 0.01),
                "agents": float(agents),
                "rule_id": rule,
                "support_mean_delta": mean_delta,
                "support_rows": rows,
                "support_better": better,
                "support_equal": equal,
                "support_worse": worse,
                "source": "repair5e2_builtin_caseb_static_support",
            }
        )
    return out


def write_recovery_csv(path: Path, specs: list[dict[str, Any]]) -> None:
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in specs:
            writer.writerow({key: row[key] for key in fields})


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.2 Guarded Selector Diagnostic\n\n")
        handle.write("- diagnostic-only = `true`\n")
        handle.write("- phase5p5_allowed = `false`\n")
        handle.write("- phase6_allowed = `false`\n")
        handle.write("- solver_semantic_changes = `false`\n")
        handle.write("- output_space = `existing_8_rules_plus_additive_defer`\n")
        handle.write("- bounded_delta_updateparams = `false`\n\n")
        handle.write("## Runtime\n\n")
        handle.write(f"- source runtime: `{summary['source_runtime_dir']}`\n")
        handle.write(f"- output runtime: `{summary['runtime_dir']}`\n")
        handle.write("- OOD guard: enabled by `--laur-ood-z-threshold`\n")
        handle.write("- guard stat overrides: `entropy_edge_usage`, `has_solution_before`, `improved_last_iteration`\n\n")
        handle.write("## Recovery Rules\n\n")
        handle.write("| map | agents | rule | mean delta | better/equal/worse |\n")
        handle.write("|---|---:|---|---:|---:|\n")
        for row in summary["recovery_rules"]:
            handle.write(
                f"| {row['map']} | {int(row['agents'])} | {row['rule_id']} | "
                f"{row['support_mean_delta']} | "
                f"{row['support_better']}/{row['support_equal']}/{row['support_worse']} |\n"
            )
        handle.write("\nUnsupported contexts defer to `additive_ltm`; `commit_heavy` is never introduced by the recovery layer.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-runtime-dir", type=Path, default=Path(DEFAULT_SOURCE))
    parser.add_argument("--output-runtime-dir", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--previous-raw-jsonl", type=Path, default=Path(DEFAULT_PREVIOUS_RAW_JSONL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source = resolve_path(args.source_runtime_dir, root)
    output = resolve_path(args.output_runtime_dir, root)
    previous_raw = resolve_path(args.previous_raw_jsonl, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)

    if not source.exists():
        raise FileNotFoundError(source)
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

    specs = build_recovery_specs(root, read_jsonl(previous_raw))
    if not specs:
        specs = fallback_specs(root)
    write_recovery_csv(output / "repair5e2_recovery_rules.csv", specs)
    guard_overrides = [
        {"feature_name": "entropy_edge_usage", "mean": 6.5, "std": 1.0},
        {"feature_name": "has_solution_before", "mean": 0.5, "std": 0.5},
        {"feature_name": "improved_last_iteration", "mean": 0.5, "std": 0.5},
    ]
    with (output / "ood_feature_stats_override.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["feature_name", "mean", "std"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(guard_overrides)

    summary = {
        "schema_version": "phase5p5_repair5e2_guarded_selector_runtime_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "output_space": "existing_8_rules_plus_additive_defer",
        "source_runtime_dir": str(source.relative_to(root)),
        "runtime_dir": str(output.relative_to(root)),
        "previous_raw_jsonl": str(previous_raw.relative_to(root)) if previous_raw.exists() else str(previous_raw),
        "recovery_rules": specs,
        "ood_feature_stat_overrides": guard_overrides,
        "notes": [
            "Uses Repair5D distilled runtime as the base scorer.",
            "Keeps the existing OOD/defer guard; unsupported or OOD contexts defer to additive_ltm.",
            "Adds a deterministic oracle/static support allowlist to prevent commit_heavy collapse.",
            "Does not implement bounded delta UpdateParams or richer LTM representation.",
        ],
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    manifest = output / "repair5e2_guarded_selector_manifest.json"
    manifest.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"runtime_dir": str(output), "summary_json": str(summary_json), "report": str(report)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
