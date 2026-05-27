"""Build stable tie-aware Phase4F LAU-LTM targets from probe deltas."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.update_sequences import validate_update_dataset_row  # noqa: E402


DEFAULT_RULE_PRIORITY = [
    "additive_ltm",
    "commit_heavy",
    "block_heavy",
    "wait_light",
    "wait_heavy",
    "block_light",
    "decay_095",
    "decay_090",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: JSONL row must be an object")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def group_by_checkpoint(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def finite_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def sorted_probe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (finite_float(row.get("delta_ratio_vs_additive"), float("-inf")), str(row.get("rule_id", ""))),
        reverse=True,
    )


def stable_rule_for_probe_group(
    probe_rows: list[dict[str, Any]],
    *,
    tie_epsilon: float,
    neutral_delta_threshold: float,
    rule_priority: list[str] | None = None,
    prefer_additive_if_tied: bool = True,
) -> dict[str, Any]:
    ordered = sorted_probe_rows(probe_rows)
    if not ordered:
        raise ValueError("probe group is empty")
    deltas = {
        str(row["rule_id"]): finite_float(row.get("delta_ratio_vs_additive"))
        for row in ordered
        if row.get("rule_id")
    }
    best_rule = str(ordered[0]["rule_id"])
    best_delta = deltas[best_rule]
    tie_rules = [
        rule_id
        for rule_id, delta in deltas.items()
        if best_delta - delta <= float(tie_epsilon)
    ]
    priority = list(rule_priority or DEFAULT_RULE_PRIORITY)
    if best_delta < float(neutral_delta_threshold):
        stable_rule = "neutral_additive"
        stable_executable = "additive_ltm"
        stable_delta = 0.0
        reason = "best_below_neutral_threshold"
    elif prefer_additive_if_tied and "additive_ltm" in tie_rules:
        stable_rule = "neutral_additive"
        stable_executable = "additive_ltm"
        stable_delta = deltas.get("additive_ltm", 0.0)
        reason = "additive_within_tie_band"
    else:
        stable_executable = next((rule_id for rule_id in priority if rule_id in tie_rules), best_rule)
        stable_rule = stable_executable
        stable_delta = deltas.get(stable_executable, best_delta)
        reason = "priority_tie_break"
    return {
        "stable_rule": stable_rule,
        "stable_executable": stable_executable,
        "stable_delta": stable_delta,
        "best_rule": best_rule,
        "best_delta": best_delta,
        "best_minus_stable": best_delta - stable_delta,
        "tie_rules": tie_rules,
        "tie_count": len(tie_rules),
        "reason": reason,
    }


def build_stable_target_rows(
    dataset_rows: list[dict[str, Any]],
    probe_rows: list[dict[str, Any]],
    *,
    tie_epsilon: float,
    neutral_delta_threshold: float,
    rule_priority: list[str] | None = None,
    prefer_additive_if_tied: bool = True,
) -> list[dict[str, Any]]:
    probe_groups = group_by_checkpoint(probe_rows)
    output: list[dict[str, Any]] = []
    for row in dataset_rows:
        checkpoint_id = str(row["checkpoint_id"])
        probes = probe_groups.get(checkpoint_id, [])
        if not probes:
            continue
        stable = stable_rule_for_probe_group(
            probes,
            tie_epsilon=tie_epsilon,
            neutral_delta_threshold=neutral_delta_threshold,
            rule_priority=rule_priority,
            prefer_additive_if_tied=prefer_additive_if_tied,
        )
        new_row = json.loads(json.dumps(row))
        target = dict(new_row["target"])
        original_target = {
            "rule_class": target["rule_class"],
            "rule_class_index": target["rule_class_index"],
            "best_rule_id": target.get("best_rule_id"),
            "delta_ratio_best": target.get("delta_ratio_best"),
            "label_confidence": target.get("label_confidence"),
            "neutral": target.get("neutral"),
        }
        stable_rule = str(stable["stable_rule"])
        rule_vocab = list(target["rule_vocab"])
        if stable_rule not in rule_vocab:
            rule_vocab.append(stable_rule)
        target["rule_vocab"] = rule_vocab
        target["rule_class"] = stable_rule
        target["rule_class_index"] = int(rule_vocab.index(stable_rule))
        target["best_rule_id"] = str(stable["stable_executable"])
        target["neutral"] = stable_rule == "neutral_additive"
        target["delta_ratio_best"] = float(stable["stable_delta"])
        target["label_confidence"] = abs(float(stable["stable_delta"]))
        target["stable_target"] = {
            "schema_version": "phase4_laur_stable_target_v1",
            "original_target": original_target,
            "tie_epsilon": float(tie_epsilon),
            "neutral_delta_threshold": float(neutral_delta_threshold),
            "prefer_additive_if_tied": bool(prefer_additive_if_tied),
            "rule_priority": list(rule_priority or DEFAULT_RULE_PRIORITY),
            "stable_rule": stable_rule,
            "stable_executable": str(stable["stable_executable"]),
            "stable_delta": float(stable["stable_delta"]),
            "best_rule": str(stable["best_rule"]),
            "best_delta": float(stable["best_delta"]),
            "best_minus_stable": float(stable["best_minus_stable"]),
            "tie_rules": list(stable["tie_rules"]),
            "tie_count": int(stable["tie_count"]),
            "reason": str(stable["reason"]),
            "changed_rule_class": stable_rule != original_target["rule_class"],
        }
        new_row["target"] = target
        output.append(new_row)
    return output


def audit_rows(rows: list[dict[str, Any]], expected_rows: int | None = None) -> dict[str, Any]:
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        errors.extend(f"row {index}: {error}" for error in validate_update_dataset_row(row))
    split_counts = Counter(str(row["split"]) for row in rows)
    label_distribution = Counter(str(row["target"]["rule_class"]) for row in rows)
    original_distribution = Counter(
        str(row["target"]["stable_target"]["original_target"]["rule_class"]) for row in rows
    )
    changed_count = sum(1 for row in rows if row["target"]["stable_target"]["changed_rule_class"])
    reason_distribution = Counter(str(row["target"]["stable_target"]["reason"]) for row in rows)
    best_minus_stable = [float(row["target"]["stable_target"]["best_minus_stable"]) for row in rows]
    result = {
        "schema_version": "phase4_laur_stable_target_audit_v1",
        "sample_count": len(rows),
        "expected_rows": expected_rows,
        "missing_rows": max(0, int(expected_rows) - len(rows)) if expected_rows is not None else None,
        "split_counts": dict(sorted(split_counts.items())),
        "label_distribution": dict(sorted(label_distribution.items())),
        "original_label_distribution": dict(sorted(original_distribution.items())),
        "changed_rule_class_count": changed_count,
        "changed_rule_class_rate": changed_count / len(rows) if rows else None,
        "reason_distribution": dict(sorted(reason_distribution.items())),
        "mean_best_minus_stable": sum(best_minus_stable) / len(best_minus_stable) if best_minus_stable else None,
        "max_best_minus_stable": max(best_minus_stable) if best_minus_stable else None,
        "schema_error_count": len(errors),
        "schema_errors": errors[:50],
    }
    result["passed"] = bool(rows) and not errors
    return result


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["split"]), str(row["map_name"]))].append(row)
    fieldnames = [
        "split",
        "map_name",
        "sample_count",
        "changed_rule_class_count",
        "changed_rule_class_rate",
        "label_distribution",
        "reason_distribution",
        "mean_best_minus_stable",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for (split, map_name), values in sorted(grouped.items()):
            changed = sum(1 for row in values if row["target"]["stable_target"]["changed_rule_class"])
            regrets = [float(row["target"]["stable_target"]["best_minus_stable"]) for row in values]
            writer.writerow(
                {
                    "split": split,
                    "map_name": map_name,
                    "sample_count": len(values),
                    "changed_rule_class_count": changed,
                    "changed_rule_class_rate": changed / len(values) if values else 0.0,
                    "label_distribution": json.dumps(
                        dict(sorted(Counter(row["target"]["rule_class"] for row in values).items())),
                        sort_keys=True,
                    ),
                    "reason_distribution": json.dumps(
                        dict(sorted(Counter(row["target"]["stable_target"]["reason"] for row in values).items())),
                        sort_keys=True,
                    ),
                    "mean_best_minus_stable": sum(regrets) / len(regrets) if regrets else None,
                }
            )


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--tie-epsilon", type=float, default=0.01)
    parser.add_argument("--neutral-delta-threshold", type=float, default=0.005)
    parser.add_argument("--rule-priority", default=",".join(DEFAULT_RULE_PRIORITY))
    parser.add_argument("--no-prefer-additive-if-tied", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    probe_path = resolve_path(args.probes, root)
    output_path = resolve_path(args.output_jsonl, root)
    summary_json_path = resolve_path(args.summary_json, root)
    summary_csv_path = resolve_path(args.summary_csv, root)
    assert dataset_path and probe_path and output_path and summary_json_path and summary_csv_path
    dataset_rows = read_jsonl(dataset_path)
    probe_rows = read_jsonl(probe_path)
    priority = [item.strip() for item in str(args.rule_priority).split(",") if item.strip()]
    stable_rows = build_stable_target_rows(
        dataset_rows,
        probe_rows,
        tie_epsilon=float(args.tie_epsilon),
        neutral_delta_threshold=float(args.neutral_delta_threshold),
        rule_priority=priority,
        prefer_additive_if_tied=not bool(args.no_prefer_additive_if_tied),
    )
    summary = audit_rows(stable_rows, expected_rows=len(dataset_rows))
    summary.update(
        {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z").strip(),
            "branch": git_value(["branch", "--show-current"], root),
            "commit": git_value(["rev-parse", "--short", "HEAD"], root),
            "dataset": str(dataset_path),
            "probes": str(probe_path),
            "output_jsonl": str(output_path),
            "tie_epsilon": float(args.tie_epsilon),
            "neutral_delta_threshold": float(args.neutral_delta_threshold),
            "rule_priority": priority,
            "prefer_additive_if_tied": not bool(args.no_prefer_additive_if_tied),
        }
    )
    if not summary["passed"]:
        raise ValueError("stable target audit failed:\n" + "\n".join(summary["schema_errors"][:20]))
    write_jsonl(output_path, stable_rows)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_summary_csv(summary_csv_path, stable_rows)
    print(json.dumps({"output_jsonl": str(output_path), "summary_json": str(summary_json_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
