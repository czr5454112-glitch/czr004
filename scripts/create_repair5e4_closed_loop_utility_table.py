"""Build the Repair5E.4 closed-loop utility table from train-support logs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5e4_train_support"
DEFAULT_FEATURE_RUNTIME = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_TABLE = "outputs/tables/phase5p5_repair5e4_closed_loop_rule_utility_train.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e4_closed_loop_rule_utility_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e4_closed_loop_rule_utility_summary.json"

CANDIDATE_RULES = [
    "additive_ltm",
    "block_heavy",
    "block_light",
    "commit_heavy",
    "decay_090",
    "decay_095",
    "wait_heavy",
    "wait_light",
]

NONADDITIVE_RULES = [rule for rule in CANDIDATE_RULES if rule != "additive_ltm"]


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


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def discover_paths(log_dir: Path) -> tuple[list[Path], list[Path]]:
    raw: list[Path] = []
    updates: list[Path] = []
    if not log_dir.exists():
        return raw, updates
    for path in sorted(log_dir.glob("*.jsonl")):
        if path.name.endswith("_commands.jsonl"):
            continue
        if path.name.endswith("_laur_updates.jsonl"):
            updates.append(path)
        else:
            raw.append(path)
    return raw, updates


def method_to_rule(method: str) -> str | None:
    if method in {"always_additive_defer", "lacam_star_ltm"}:
        return "additive_ltm"
    prefix = "oracle_probe_static_"
    if method.startswith(prefix):
        rule = method[len(prefix) :]
        return rule if rule in CANDIDATE_RULES else None
    return None


def case_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map", "")),
        int(finite(row.get("agents"), 0.0)),
        int(finite(row.get("seed"), 0.0)),
        str(row.get("scen", "")),
    )


def update_key(row: dict[str, Any]) -> tuple[str, int, int, str, int]:
    key = case_key(row)
    return (*key, int(finite(row.get("iteration"), 0.0)))


def delta(contender: dict[str, Any] | None, baseline: dict[str, Any] | None, key: str) -> float | None:
    if contender is None or baseline is None:
        return None
    if key == "success":
        return float(bool(contender.get("success"))) - float(bool(baseline.get("success")))
    value = finite(contender.get(key))
    base = finite(baseline.get(key))
    if not math.isfinite(value) or not math.isfinite(base):
        return None
    return value - base


def read_feature_names(runtime_dir: Path) -> list[str]:
    path = runtime_dir / "features.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def feature_payload(
    row: dict[str, Any],
    selector_feature_names: list[str],
) -> tuple[list[str], list[float], str, str]:
    names = [str(name) for name in row.get("runtime_feature_names", [])]
    values = [finite(value, 0.0) for value in row.get("runtime_feature_values", [])]
    by_name = {name: value for name, value in zip(names, values)}
    selector_values = [by_name.get(name, 0.0) for name in selector_feature_names] if selector_feature_names else values
    encoded = json.dumps(
        {"names": names, "values": [round(value, 8) for value in values]},
        sort_keys=True,
        separators=(",", ":"),
    )
    return (
        names,
        values,
        hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        ";".join(f"{v:.12g}" for v in selector_values),
    )


def mean(values: list[float]) -> float | None:
    finite_values = [value for value in values if math.isfinite(value)]
    return statistics.mean(finite_values) if finite_values else None


def build_group_rule_stats(
    outcomes: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]],
    epsilon_ratio: float,
    min_positive_instances: int,
) -> dict[tuple[str, int, str], dict[str, Any]]:
    by_group: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for key, methods in outcomes.items():
        baseline = methods.get("lacam_star_ltm")
        for rule in NONADDITIVE_RULES:
            row = methods.get(f"oracle_probe_static_{rule}")
            ratio_delta = delta(row, baseline, "sum_of_loss_ratio")
            success_delta = delta(row, baseline, "success")
            if ratio_delta is None or success_delta is None:
                continue
            by_group[(key[0], key[1], rule)].append(
                {
                    "seed": key[2],
                    "ratio_delta": ratio_delta,
                    "success_delta": success_delta,
                    "better": ratio_delta < -epsilon_ratio,
                    "worse": ratio_delta > epsilon_ratio or success_delta < 0,
                }
            )

    stats: dict[tuple[str, int, str], dict[str, Any]] = {}
    for key, rows in by_group.items():
        ratios = [float(row["ratio_delta"]) for row in rows]
        worse_count = sum(1 for row in rows if row["worse"])
        better_count = sum(1 for row in rows if row["better"])
        support_instances = len({int(row["seed"]) for row in rows})
        mean_ratio = mean(ratios) or 0.0
        harmful_share = worse_count / len(rows) if rows else 1.0
        rule = key[2]
        positive = (
            support_instances >= min_positive_instances
            and mean_ratio < -epsilon_ratio
            and harmful_share <= 0.25
            and all(float(row["success_delta"]) >= 0.0 for row in rows)
        )
        if rule == "commit_heavy":
            positive = positive and support_instances >= max(3, min_positive_instances * 2) and better_count >= 3
        stats[key] = {
            "rows": len(rows),
            "support_instances": support_instances,
            "mean_ratio_delta_vs_ltm": mean_ratio,
            "min_ratio_delta_vs_ltm": min(ratios) if ratios else None,
            "max_ratio_delta_vs_ltm": max(ratios) if ratios else None,
            "better": better_count,
            "worse": worse_count,
            "harmful_share": harmful_share,
            "positive_group_rule": positive,
        }
    return stats


def build_table(
    *,
    raw_rows: list[dict[str, Any]],
    update_rows: list[dict[str, Any]],
    selector_feature_names: list[str],
    epsilon_ratio: float,
    min_positive_instances: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    outcomes: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in raw_rows:
        outcomes[case_key(row)][str(row.get("method", ""))] = row

    group_stats = build_group_rule_stats(outcomes, epsilon_ratio, min_positive_instances)

    context_features: dict[tuple[str, int, int, str, int], dict[str, Any]] = {}
    for row in update_rows:
        names, values, feature_hash, feature_values = feature_payload(row, selector_feature_names)
        if not names or not values:
            continue
        key = update_key(row)
        current = context_features.get(key)
        method = str(row.get("method", ""))
        preferred = method == "always_additive_defer"
        if current is None or preferred:
            context_features[key] = {
                "runtime_feature_names": names,
                "runtime_feature_values": values,
                "runtime_feature_hash": feature_hash,
                "feature_values": feature_values,
                "feature_source_method": method,
            }

    out: list[dict[str, Any]] = []
    for key, feature_info in sorted(context_features.items()):
        base_key = key[:4]
        methods = outcomes.get(base_key, {})
        baseline = methods.get("lacam_star_ltm")
        if baseline is None:
            continue
        candidate_rows: dict[str, dict[str, Any] | None] = {
            "additive_ltm": methods.get("always_additive_defer") or baseline
        }
        for rule in NONADDITIVE_RULES:
            candidate_rows[rule] = methods.get(f"oracle_probe_static_{rule}")

        rule_diagnostics: dict[str, dict[str, Any]] = {}
        for rule in CANDIDATE_RULES:
            contender = candidate_rows.get(rule)
            ratio_delta = delta(contender, baseline, "sum_of_loss_ratio")
            success_delta = delta(contender, baseline, "success")
            safe = bool(
                success_delta is not None
                and success_delta >= 0
                and ratio_delta is not None
                and ratio_delta <= epsilon_ratio
            )
            group = group_stats.get((key[0], key[1], rule), {})
            positive = bool(
                rule != "additive_ltm"
                and safe
                and ratio_delta is not None
                and ratio_delta < -epsilon_ratio
                and group.get("positive_group_rule")
            )
            rule_diagnostics[rule] = {
                "success_delta_vs_ltm": success_delta,
                "ratio_delta_vs_ltm": ratio_delta,
                "expanded_delta_vs_ltm": delta(contender, baseline, "expanded_nodes"),
                "pibt_delta_vs_ltm": delta(contender, baseline, "low_level_pibt_calls"),
                "ttfs_delta_vs_ltm": delta(contender, baseline, "time_to_first_solution_ms"),
                "non_additive_flag": int(rule != "additive_ltm"),
                "safe_nonregression_flag": int(safe),
                "positive_utility_flag": int(positive),
            }

        positives = [
            (rule, rule_diagnostics[rule]["ratio_delta_vs_ltm"])
            for rule in NONADDITIVE_RULES
            if rule_diagnostics[rule]["positive_utility_flag"]
            and rule_diagnostics[rule]["ratio_delta_vs_ltm"] is not None
        ]
        if positives:
            label_rule, best_delta = min(positives, key=lambda item: float(item[1]))
            positive_margin = max(0.0, -float(best_delta))
        else:
            label_rule = "additive_ltm"
            positive_margin = 0.0

        row_out: dict[str, Any] = {
            "map": key[0],
            "agents": key[1],
            "instance_id": key[2],
            "scen": key[3],
            "iteration": key[4],
            "update_index": key[4],
            "context_hash": hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest(),
            "runtime_feature_hash": feature_info["runtime_feature_hash"],
            "runtime_feature_names": json.dumps(feature_info["runtime_feature_names"], separators=(",", ":")),
            "runtime_feature_values": json.dumps(feature_info["runtime_feature_values"], separators=(",", ":")),
            "feature_values": feature_info["feature_values"],
            "feature_source_method": feature_info["feature_source_method"],
            "label_rule": label_rule,
            "positive_margin_ratio": positive_margin,
        }
        for rule in CANDIDATE_RULES:
            for metric, value in rule_diagnostics[rule].items():
                row_out[f"{rule}_{metric}"] = value
            group = group_stats.get((key[0], key[1], rule), {})
            row_out[f"{rule}_group_support_instances"] = group.get("support_instances", 0)
            row_out[f"{rule}_group_mean_ratio_delta_vs_ltm"] = group.get("mean_ratio_delta_vs_ltm")
        out.append(row_out)

    label_counts = Counter(str(row["label_rule"]) for row in out)
    group_counts = Counter((str(row["map"]), int(row["agents"])) for row in out if row["label_rule"] != "additive_ltm")
    summary = {
        "schema_version": "phase5p5_repair5e4_closed_loop_rule_utility_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "epsilon_ratio": epsilon_ratio,
        "min_positive_instances": min_positive_instances,
        "raw_rows": len(raw_rows),
        "update_rows": len(update_rows),
        "contexts": len(out),
        "positive_nonadditive_contexts": sum(1 for row in out if row["label_rule"] != "additive_ltm"),
        "positive_nonadditive_contexts_per_map_agent": {
            f"{key[0]}:{key[1]}": value for key, value in sorted(group_counts.items())
        },
        "rule_distribution_among_positive_labels": {
            rule: count for rule, count in sorted(label_counts.items()) if rule != "additive_ltm"
        },
        "label_distribution": dict(sorted(label_counts.items())),
        "commit_heavy_positive_share": (
            label_counts.get("commit_heavy", 0) / max(1, sum(count for rule, count in label_counts.items() if rule != "additive_ltm"))
        ),
        "support_per_rule": {
            f"{key[0]}:{key[1]}:{key[2]}": value for key, value in sorted(group_stats.items())
        },
        "support_per_instance": len({(row["map"], row["agents"], row["instance_id"]) for row in out}),
        "oracle_label_entropy": entropy(label_counts),
        "cases_where_oracle_positive_but_every_fixed_rule_group_neutral": 0,
        "selector_feature_names": selector_feature_names,
    }
    return out, summary


def entropy(counter: Counter[str]) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    value = 0.0
    for count in counter.values():
        if count <= 0:
            continue
        p = count / total
        value -= p * math.log2(p)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = [
        "map",
        "agents",
        "instance_id",
        "scen",
        "iteration",
        "update_index",
        "context_hash",
        "runtime_feature_hash",
        "runtime_feature_names",
        "runtime_feature_values",
        "feature_values",
        "feature_source_method",
        "label_rule",
        "positive_margin_ratio",
    ]
    for rule in CANDIDATE_RULES:
        fields.extend(
            [
                f"{rule}_success_delta_vs_ltm",
                f"{rule}_ratio_delta_vs_ltm",
                f"{rule}_expanded_delta_vs_ltm",
                f"{rule}_pibt_delta_vs_ltm",
                f"{rule}_ttfs_delta_vs_ltm",
                f"{rule}_non_additive_flag",
                f"{rule}_safe_nonregression_flag",
                f"{rule}_positive_utility_flag",
                f"{rule}_group_support_instances",
                f"{rule}_group_mean_ratio_delta_vs_ltm",
            ]
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.4 Closed-Loop Rule Utility Table\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- contexts: `{summary['contexts']}`\n")
        handle.write(f"- positive non-additive contexts: `{summary['positive_nonadditive_contexts']}`\n")
        handle.write(f"- epsilon_ratio: `{summary['epsilon_ratio']}`\n")
        handle.write(f"- label distribution: `{summary['label_distribution']}`\n\n")
        handle.write("## Positive Labels By Group\n\n")
        handle.write(json.dumps(summary["positive_nonadditive_contexts_per_map_agent"], indent=2, sort_keys=True))
        handle.write("\n\n## Rule Distribution Among Positive Labels\n\n")
        handle.write(json.dumps(summary["rule_distribution_among_positive_labels"], indent=2, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=Path(DEFAULT_LOG_DIR))
    parser.add_argument("--feature-runtime-dir", type=Path, default=Path(DEFAULT_FEATURE_RUNTIME))
    parser.add_argument("--raw-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--update-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_TABLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--epsilon-ratio", type=float, default=0.001)
    parser.add_argument("--min-positive-instances", type=int, default=2)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    log_dir = resolve_path(args.log_dir, root)
    feature_runtime = resolve_path(args.feature_runtime_dir, root)
    selector_feature_names = read_feature_names(feature_runtime)
    discovered_raw, discovered_updates = discover_paths(log_dir)
    raw_paths = [resolve_path(path, root) for path in args.raw_jsonl] or discovered_raw
    update_paths = [resolve_path(path, root) for path in args.update_jsonl] or discovered_updates
    raw_rows = [row for path in raw_paths for row in read_jsonl(path)]
    update_rows = [row for path in update_paths for row in read_jsonl(path)]
    rows, summary = build_table(
        raw_rows=raw_rows,
        update_rows=update_rows,
        selector_feature_names=selector_feature_names,
        epsilon_ratio=float(args.epsilon_ratio),
        min_positive_instances=int(args.min_positive_instances),
    )
    output_csv = resolve_path(args.output_csv, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    write_csv(output_csv, rows)
    summary.update(
        {
            "inputs": {
                "raw_jsonl": [rel(path, root) for path in raw_paths],
                "update_jsonl": [rel(path, root) for path in update_paths],
                "feature_runtime_dir": rel(feature_runtime, root),
            },
            "outputs": {
                "table_csv": rel(output_csv, root),
                "report": rel(report, root),
                "summary_json": rel(summary_json, root),
            },
            "file_hashes": {
                "raw_jsonl": {rel(path, root): sha256_file(path) for path in raw_paths},
                "update_jsonl": {rel(path, root): sha256_file(path) for path in update_paths},
                "table_csv": sha256_file(output_csv),
            },
        }
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps(summary["outputs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
