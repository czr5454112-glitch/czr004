"""Build Repair5E.5 soft/listwise cross-fold utility tables."""

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


DEFAULT_SUPPORT_SUMMARY = "outputs/reports/phase5p5_repair5e5_crossfold_support_summary.json"
DEFAULT_FEATURE_RUNTIME = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_LONG_CSV = "outputs/tables/phase5p5_repair5e5_crossfold_utility_long.csv"
DEFAULT_WIDE_CSV = "outputs/tables/phase5p5_repair5e5_crossfold_utility_wide.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e5_crossfold_utility_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e5_crossfold_utility_summary.json"

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


def finite_int(value: Any, default: int = 0) -> int:
    number = finite(value)
    return int(number) if math.isfinite(number) else default


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.mean(clean) if clean else None


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
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


def method_to_rule(method: str) -> str | None:
    if method == "lacam_star_ltm":
        return "lacam_star_ltm"
    if method == "always_additive_defer":
        return "additive_ltm"
    prefix = "oracle_probe_static_"
    if method.startswith(prefix):
        rule = method[len(prefix) :]
        return rule if rule in CANDIDATE_RULES else None
    return None


def case_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map", "")),
        finite_int(row.get("agents")),
        finite_int(row.get("seed")),
        str(row.get("scen", "")),
    )


def update_key(row: dict[str, Any]) -> tuple[str, int, int, str, int]:
    return (*case_key(row), finite_int(row.get("iteration")))


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
        ";".join(f"{value:.12g}" for value in selector_values),
    )


def build_outcomes(raw_rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, dict[str, Any]]]:
    outcomes: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in raw_rows:
        rule = method_to_rule(str(row.get("method", "")))
        if rule is None:
            continue
        outcomes[case_key(row)][rule] = row
    return outcomes


def build_group_rule_stats(
    outcomes: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]],
    *,
    epsilon_ratio: float,
    max_harmful_share: float,
    min_positive_instances: int,
) -> dict[tuple[str, int, str], dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for key, methods in outcomes.items():
        baseline = methods.get("lacam_star_ltm")
        if baseline is None:
            continue
        for rule in NONADDITIVE_RULES:
            contender = methods.get(rule)
            ratio_delta = delta(contender, baseline, "sum_of_loss_ratio")
            success_delta = delta(contender, baseline, "success")
            if ratio_delta is None or success_delta is None:
                continue
            grouped[(key[0], key[1], rule)].append(
                {
                    "seed": key[2],
                    "ratio_delta": float(ratio_delta),
                    "success_delta": float(success_delta),
                    "better": float(ratio_delta) < -epsilon_ratio and float(success_delta) >= 0.0,
                    "worse": float(ratio_delta) > epsilon_ratio or float(success_delta) < 0.0,
                }
            )
    stats: dict[tuple[str, int, str], dict[str, Any]] = {}
    for key, rows in grouped.items():
        ratios = [float(row["ratio_delta"]) for row in rows]
        support_instances = len({int(row["seed"]) for row in rows})
        better = sum(1 for row in rows if row["better"])
        worse = sum(1 for row in rows if row["worse"])
        harmful_share = worse / len(rows) if rows else 1.0
        mean_ratio = mean(ratios) or 0.0
        stable = (
            support_instances >= min_positive_instances
            and mean_ratio < -epsilon_ratio
            and harmful_share <= max_harmful_share
            and better > worse
            and all(float(row["success_delta"]) >= 0.0 for row in rows)
        )
        if key[2] == "commit_heavy":
            stable = False
        stats[key] = {
            "support_count": len(rows),
            "support_instances": support_instances,
            "support_better": better,
            "support_worse": worse,
            "mean_ratio_delta_vs_ltm": mean_ratio,
            "min_ratio_delta_vs_ltm": min(ratios) if ratios else None,
            "max_ratio_delta_vs_ltm": max(ratios) if ratios else None,
            "false_positive_risk": harmful_share,
            "stable_positive": stable,
            "beats_additive_epsilon_count": sum(1 for value in ratios if value < -epsilon_ratio),
        }
    return stats


def rank_rules(metrics: dict[str, dict[str, Any]]) -> dict[str, int]:
    def score(rule: str) -> tuple[int, float, float, float, str]:
        row = metrics[rule]
        success_delta = row.get("success_delta_vs_ltm")
        ratio_delta = row.get("utility_delta_ratio")
        expanded_delta = row.get("utility_delta_expanded")
        pibt_delta = row.get("utility_delta_pibt")
        unsafe = 1 if success_delta is None or float(success_delta) < 0.0 else 0
        return (
            unsafe,
            float(ratio_delta) if ratio_delta is not None else float("inf"),
            float(expanded_delta) if expanded_delta is not None else float("inf"),
            float(pibt_delta) if pibt_delta is not None else float("inf"),
            rule,
        )

    ordered = sorted(CANDIDATE_RULES, key=score)
    return {rule: index + 1 for index, rule in enumerate(ordered)}


def build_tables(
    *,
    support_summary: dict[str, Any],
    selector_feature_names: list[str],
    epsilon_ratio: float,
    max_harmful_share: float,
    min_positive_instances: int,
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    fold_payloads: dict[int, dict[str, Any]] = {}
    group_stats_by_fold: dict[int, dict[tuple[str, int, str], dict[str, Any]]] = {}
    for fold_name, fold in sorted((support_summary.get("folds") or {}).items()):
        fold_id = int(str(fold_name).split("_")[-1])
        raw_path = resolve_path(fold["raw_jsonl"], root)
        update_path = resolve_path(fold["update_jsonl"], root)
        raw_rows = read_jsonl(raw_path)
        update_rows = read_jsonl(update_path)
        outcomes = build_outcomes(raw_rows)
        group_stats = build_group_rule_stats(
            outcomes,
            epsilon_ratio=epsilon_ratio,
            max_harmful_share=max_harmful_share,
            min_positive_instances=min_positive_instances,
        )
        fold_payloads[fold_id] = {
            "fold": fold,
            "raw_path": raw_path,
            "update_path": update_path,
            "raw_rows": raw_rows,
            "update_rows": update_rows,
            "outcomes": outcomes,
        }
        group_stats_by_fold[fold_id] = group_stats

    fold_agreement: Counter[tuple[str, int, str]] = Counter()
    for group_stats in group_stats_by_fold.values():
        for key, stats in group_stats.items():
            if stats.get("stable_positive"):
                fold_agreement[key] += 1

    long_rows: list[dict[str, Any]] = []
    wide_rows: list[dict[str, Any]] = []
    positive_counts: Counter[tuple[str, int, str, int]] = Counter()
    margin_values: list[float] = []
    weak_non_ratio_benefits: Counter[str] = Counter()

    for fold_id, payload in sorted(fold_payloads.items()):
        outcomes = payload["outcomes"]
        group_stats = group_stats_by_fold[fold_id]
        context_features: dict[tuple[str, int, int, str, int], dict[str, Any]] = {}
        for row in payload["update_rows"]:
            names, values, feature_hash, feature_values = feature_payload(row, selector_feature_names)
            if not names or not values:
                continue
            key = update_key(row)
            method = str(row.get("method", ""))
            current = context_features.get(key)
            preferred = method == "always_additive_defer"
            if current is None or preferred:
                context_features[key] = {
                    "runtime_feature_names": names,
                    "runtime_feature_values": values,
                    "runtime_feature_hash": feature_hash,
                    "feature_values": feature_values,
                    "feature_source_method": method,
                }

        for key, feature_info in sorted(context_features.items()):
            base_key = key[:4]
            methods = outcomes.get(base_key, {})
            baseline = methods.get("lacam_star_ltm")
            if baseline is None:
                continue
            metrics: dict[str, dict[str, Any]] = {}
            for rule in CANDIDATE_RULES:
                contender = (methods.get("additive_ltm") or baseline) if rule == "additive_ltm" else methods.get(rule)
                ratio_delta = delta(contender, baseline, "sum_of_loss_ratio")
                success_delta = delta(contender, baseline, "success")
                expanded_delta = delta(contender, baseline, "expanded_nodes")
                pibt_delta = delta(contender, baseline, "low_level_pibt_calls")
                ttfs_delta = delta(contender, baseline, "time_to_first_solution_ms")
                safe = (
                    success_delta is not None
                    and float(success_delta) >= 0.0
                    and ratio_delta is not None
                    and float(ratio_delta) <= epsilon_ratio
                )
                group = group_stats.get((key[0], key[1], rule), {})
                margin = max(0.0, -float(ratio_delta)) if ratio_delta is not None else 0.0
                if rule != "additive_ltm" and ratio_delta is not None and abs(float(ratio_delta)) <= epsilon_ratio:
                    if (expanded_delta is not None and float(expanded_delta) < 0.0) or (
                        pibt_delta is not None and float(pibt_delta) < 0.0
                    ):
                        weak_non_ratio_benefits[f"{key[0]}:{key[1]}:{rule}"] += 1
                metrics[rule] = {
                    "utility_delta_ratio": ratio_delta,
                    "utility_delta_expanded": expanded_delta,
                    "utility_delta_pibt": pibt_delta,
                    "utility_delta_ttfs": ttfs_delta,
                    "success_delta_vs_ltm": success_delta,
                    "success_by_rule": bool(contender.get("success")) if contender is not None else False,
                    "safe_by_rule": safe,
                    "margin_to_additive_by_rule": margin,
                    "support_count": int(group.get("support_count", 0) or 0),
                    "support_instances": int(group.get("support_instances", 0) or 0),
                    "false_positive_risk": float(group.get("false_positive_risk", 1.0) or 1.0),
                    "stable_positive": bool(group.get("stable_positive", False)),
                    "fold_agreement": int(fold_agreement.get((key[0], key[1], rule), 0)),
                    "support_mean_ratio_delta": group.get("mean_ratio_delta_vs_ltm"),
                }

            ranks = rank_rules(metrics)
            second_best_margin = 0.0
            ordered_margins = sorted((metrics[rule]["margin_to_additive_by_rule"], rule) for rule in NONADDITIVE_RULES)
            positive_candidates = [
                rule
                for rule in NONADDITIVE_RULES
                if metrics[rule]["safe_by_rule"]
                and metrics[rule]["margin_to_additive_by_rule"] > epsilon_ratio
                and metrics[rule]["stable_positive"]
            ]
            best_nonadditive = (
                max(positive_candidates, key=lambda rule: metrics[rule]["margin_to_additive_by_rule"])
                if positive_candidates
                else "additive_ltm"
            )
            predicted_margin = (
                float(metrics[best_nonadditive]["margin_to_additive_by_rule"])
                if best_nonadditive != "additive_ltm"
                else 0.0
            )
            nonadditive_margins = sorted(
                [float(metrics[rule]["margin_to_additive_by_rule"]) for rule in NONADDITIVE_RULES],
                reverse=True,
            )
            if len(nonadditive_margins) >= 2:
                second_best_margin = nonadditive_margins[0] - nonadditive_margins[1]
            margin_values.append(predicted_margin)
            if best_nonadditive != "additive_ltm":
                positive_counts[(key[0], key[1], best_nonadditive, fold_id)] += 1

            base_common = {
                "map": key[0],
                "agents": key[1],
                "instance_id": key[2],
                "scen": key[3],
                "iteration": key[4],
                "update_index": key[4],
                "fold_id": fold_id,
                "context_hash": hashlib.sha256(json.dumps([fold_id, *key], sort_keys=True).encode("utf-8")).hexdigest(),
                "runtime_feature_hash": feature_info["runtime_feature_hash"],
                "runtime_feature_names": json.dumps(feature_info["runtime_feature_names"], separators=(",", ":")),
                "runtime_feature_values": json.dumps(feature_info["runtime_feature_values"], separators=(",", ":")),
                "context_feature_vector": feature_info["feature_values"],
                "feature_values": feature_info["feature_values"],
                "feature_source_method": feature_info["feature_source_method"],
                "best_nonadditive_rule": best_nonadditive,
                "predicted_margin_ratio": predicted_margin,
                "margin_to_second_best": second_best_margin,
            }
            wide = dict(base_common)
            for rule in CANDIDATE_RULES:
                metric = metrics[rule]
                for metric_name, value in metric.items():
                    wide[f"{rule}_{metric_name}"] = value
                wide[f"{rule}_rank_by_rule"] = ranks[rule]
            wide_rows.append(wide)

            for rule in CANDIDATE_RULES:
                metric = metrics[rule]
                long = dict(base_common)
                long.update(
                    {
                        "rule_id": rule,
                        "utility_delta_ratio_by_rule": metric["utility_delta_ratio"],
                        "utility_delta_expanded_by_rule": metric["utility_delta_expanded"],
                        "utility_delta_pibt_by_rule": metric["utility_delta_pibt"],
                        "utility_delta_ttfs_by_rule": metric["utility_delta_ttfs"],
                        "success_by_rule": metric["success_by_rule"],
                        "safe_by_rule": metric["safe_by_rule"],
                        "rank_by_rule": ranks[rule],
                        "margin_to_additive_by_rule": metric["margin_to_additive_by_rule"],
                        "support_count": metric["support_count"],
                        "support_instances": metric["support_instances"],
                        "false_positive_risk": metric["false_positive_risk"],
                        "stable_positive": metric["stable_positive"],
                        "fold_agreement": metric["fold_agreement"],
                        "support_mean_ratio_delta": metric["support_mean_ratio_delta"],
                    }
                )
                long_rows.append(long)

    rule_false_positive_risk = {
        rule: mean(
            [
                float(row[f"{rule}_false_positive_risk"])
                for row in wide_rows
                if f"{rule}_false_positive_risk" in row
            ]
        )
        for rule in NONADDITIVE_RULES
    }
    stable_positive_count = Counter(row["rule_id"] for row in long_rows if row["stable_positive"])
    beats_additive_count = Counter(
        row["rule_id"]
        for row in long_rows
        if row["rule_id"] != "additive_ltm"
        and row["utility_delta_ratio_by_rule"] is not None
        and float(row["utility_delta_ratio_by_rule"]) < -epsilon_ratio
    )
    positive_maps = sorted({str(row["map"]) for row in wide_rows if row["best_nonadditive_rule"] != "additive_ltm"})
    summary = {
        "schema_version": "phase5p5_repair5e5_crossfold_utility_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "epsilon_ratio": epsilon_ratio,
        "max_harmful_share": max_harmful_share,
        "min_positive_instances": min_positive_instances,
        "wide_rows": len(wide_rows),
        "long_rows": len(long_rows),
        "positive_context_count_by_map_agents_rule_fold": {
            f"{key[0]}:{key[1]}:{key[2]}:fold_{key[3]}": value for key, value in sorted(positive_counts.items())
        },
        "stable_positive_count_by_rule": dict(sorted(stable_positive_count.items())),
        "false_positive_risk_by_rule": rule_false_positive_risk,
        "beats_additive_by_more_than_epsilon_by_rule": dict(sorted(beats_additive_count.items())),
        "utility_margin_histogram": histogram(margin_values),
        "positive_labels_only_random_map": bool(positive_maps and set(positive_maps) <= {"random-32-32-20"}),
        "positive_label_maps": positive_maps,
        "maze_warehouse_weak_non_ratio_benefits": dict(sorted(weak_non_ratio_benefits.items())),
        "support_summary": support_summary.get("schema_version"),
        "support_leakage_detected": support_summary.get("leakage_detected"),
    }
    return long_rows, wide_rows, summary


def histogram(values: list[float]) -> dict[str, int]:
    bins = {
        "0": 0,
        "(0,0.001]": 0,
        "(0.001,0.002]": 0,
        "(0.002,0.005]": 0,
        ">0.005": 0,
    }
    for value in values:
        if value <= 0.0:
            bins["0"] += 1
        elif value <= 0.001:
            bins["(0,0.001]"] += 1
        elif value <= 0.002:
            bins["(0.001,0.002]"] += 1
        elif value <= 0.005:
            bins["(0.002,0.005]"] += 1
        else:
            bins[">0.005"] += 1
    return bins


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.5 Cross-Fold Utility Tables\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- wide_rows: `{summary['wide_rows']}`\n")
        handle.write(f"- long_rows: `{summary['long_rows']}`\n")
        handle.write(f"- positive_labels_only_random_map: `{summary['positive_labels_only_random_map']}`\n")
        handle.write(f"- positive_label_maps: `{summary['positive_label_maps']}`\n\n")
        handle.write("## Stable Positives By Rule\n\n")
        handle.write(json.dumps(summary["stable_positive_count_by_rule"], indent=2, sort_keys=True))
        handle.write("\n\n## False-Positive Risk By Rule\n\n")
        handle.write(json.dumps(summary["false_positive_risk_by_rule"], indent=2, sort_keys=True))
        handle.write("\n\n## Margin Histogram\n\n")
        handle.write(json.dumps(summary["utility_margin_histogram"], indent=2, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-summary-json", type=Path, default=Path(DEFAULT_SUPPORT_SUMMARY))
    parser.add_argument("--feature-runtime-dir", type=Path, default=Path(DEFAULT_FEATURE_RUNTIME))
    parser.add_argument("--long-csv", type=Path, default=Path(DEFAULT_LONG_CSV))
    parser.add_argument("--wide-csv", type=Path, default=Path(DEFAULT_WIDE_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--epsilon-ratio", type=float, default=0.001)
    parser.add_argument("--max-harmful-share", type=float, default=0.25)
    parser.add_argument("--min-positive-instances", type=int, default=4)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    support_summary_path = resolve_path(args.support_summary_json, root)
    feature_runtime = resolve_path(args.feature_runtime_dir, root)
    long_csv = resolve_path(args.long_csv, root)
    wide_csv = resolve_path(args.wide_csv, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)

    support_summary = read_json(support_summary_path)
    selector_feature_names = read_feature_names(feature_runtime)
    long_rows, wide_rows, summary = build_tables(
        support_summary=support_summary,
        selector_feature_names=selector_feature_names,
        epsilon_ratio=float(args.epsilon_ratio),
        max_harmful_share=float(args.max_harmful_share),
        min_positive_instances=int(args.min_positive_instances),
        root=root,
    )
    write_csv(long_csv, long_rows)
    write_csv(wide_csv, wide_rows)
    summary.update(
        {
            "inputs": {
                "support_summary_json": rel(support_summary_path, root),
                "support_summary_sha256": sha256_file(support_summary_path),
                "feature_runtime_dir": rel(feature_runtime, root),
            },
            "outputs": {
                "long_csv": rel(long_csv, root),
                "long_csv_sha256": sha256_file(long_csv),
                "wide_csv": rel(wide_csv, root),
                "wide_csv_sha256": sha256_file(wide_csv),
            },
        }
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"long_csv": rel(long_csv, root), "wide_csv": rel(wide_csv, root)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
