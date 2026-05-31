"""Repair5B failure decomposition and oracle-gap diagnostics.

This is an offline-only diagnostic. It compares simple fallbacks, completed
Repair5 eval CSVs, and oracle selectors on the attention-native label dataset.
It never grants Phase5.5 or Phase6 permission.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.stable_attention_dataset_laur import read_jsonl  # noqa: E402
from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS, rule_family  # noqa: E402


DEFAULT_DATASET_CANDIDATES = [
    "artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/"
    "update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl",
    "artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/"
    "update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl",
    "artifacts/teacher/laur/full_repair5_attention_native/update_labels/phase4_laur_attention_native_dataset.jsonl",
]

DEFAULT_REPAIR5_CSV_GLOBS = [
    "outputs/tables/phase4f_repair5_attention_native_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_rawtrace_edge_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_rawtrace_edge_sf_*_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_expand5000_*_eval_seed61.csv",
]

DEFAULT_REPAIR3_CSV_GLOBS = [
    "outputs/tables/phase4f_repair3_stable_tie001_no_additive_pref_eval_h010.csv",
]

ADDITIVE_RULE = "additive_ltm"
ADDITIVE_INDEX = EXECUTABLE_RULE_IDS.index(ADDITIVE_RULE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def resolve_existing(path: str | Path, root: Path) -> Path:
    value = Path(path)
    candidate = value if value.is_absolute() else root / value
    if candidate.exists():
        return candidate
    if candidate.suffix == ".jsonl":
        compressed = candidate.with_suffix(candidate.suffix + ".zst")
        if compressed.exists():
            return compressed
    raise FileNotFoundError(candidate)


def default_dataset(root: Path) -> Path:
    for candidate in DEFAULT_DATASET_CANDIDATES:
        try:
            return resolve_existing(candidate, root)
        except FileNotFoundError:
            continue
    raise FileNotFoundError("no default Repair5 attention-native dataset found")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in {float("inf"), float("-inf")}:
        return default
    return number


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def safe_div(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def top_indices(values: list[float], *, allowed: list[bool] | None = None, k: int = 3) -> list[int]:
    pairs: list[tuple[float, int]] = []
    for index, value in enumerate(values):
        if allowed is not None and not allowed[index]:
            continue
        pairs.append((float(value), index))
    pairs.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return [index for _, index in pairs[:k]]


def oracle_best_safe_index(row: dict[str, Any]) -> int:
    utilities = [finite(value) for value in row["risk_adjusted_utility_vector"]]
    safe = [parse_bool(value) for value in row["safe_rule_mask"]]
    candidates = [index for index, ok in enumerate(safe) if ok]
    if not candidates:
        return ADDITIVE_INDEX
    return max(candidates, key=lambda index: utilities[index])


def oracle_best_safe_nonadditive_index(row: dict[str, Any]) -> int:
    utilities = [finite(value) for value in row["risk_adjusted_utility_vector"]]
    safe_nonadditive = [parse_bool(value) for value in row["safe_nonadditive_mask"]]
    candidates = [index for index, ok in enumerate(safe_nonadditive) if ok]
    if not candidates:
        return ADDITIVE_INDEX
    return max(candidates, key=lambda index: utilities[index])


def oracle_defer_when_no_safe_opportunity_index(row: dict[str, Any]) -> int:
    margin = finite(row.get("audit", {}).get("label_params", {}).get("opportunity_margin"), 0.010)
    utilities = [finite(value) for value in row["risk_adjusted_utility_vector"]]
    best_nonadditive = oracle_best_safe_nonadditive_index(row)
    if best_nonadditive == ADDITIVE_INDEX:
        return ADDITIVE_INDEX
    if utilities[best_nonadditive] - utilities[ADDITIVE_INDEX] < margin:
        return ADDITIVE_INDEX
    return best_nonadditive


def row_key(row: dict[str, Any]) -> str:
    return str(row.get("checkpoint_id", ""))


def base_context(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "split": str(row.get("split", "")),
        "run_id": str(row.get("run_id", "")),
        "checkpoint_id": str(row.get("checkpoint_id", "")),
        "map_name": str(row.get("map_name", "")),
        "agents": int(row.get("agents", 0) or 0),
        "seed": int(row.get("seed", 0) or 0),
        "iteration": int(row.get("iteration", 0) or 0),
        "decision_target": str(row.get("decision_target", "")),
        "target_rule": str(row.get("target_rule") or row.get("target", {}).get("target_rule")),
        "target_rule_index": int(row.get("target", {}).get("target_rule_index", -1)),
        "defer_reason": str(row.get("defer_reason")),
        "has_nonadditive_opportunity": bool(row.get("has_nonadditive_opportunity")),
        "has_high_margin_nonadditive_opportunity": bool(row.get("has_high_margin_nonadditive_opportunity")),
        "best_safe_nonadditive_advantage": finite(row.get("best_safe_nonadditive_advantage")),
        "opportunity_margin": finite(row.get("audit", {}).get("label_params", {}).get("opportunity_margin"), 0.010),
    }


def make_record_from_dataset(row: dict[str, Any], *, comparator: str, selected_index: int, top3: list[int]) -> dict[str, Any]:
    deltas = [finite(value) for value in row["probe_delta_vector"]]
    utilities = [finite(value) for value in row["risk_adjusted_utility_vector"]]
    harmful = [parse_bool(value) for value in row["probe_harmful_vector"]]
    selected_rule = EXECUTABLE_RULE_IDS[selected_index]
    target_index = int(row.get("target", {}).get("target_rule_index", -1))
    use_nonadditive_target = row.get("decision_target") == "use_nonadditive" and target_index >= 0
    oracle_index = oracle_best_safe_index(row)
    selected_decision = "defer_ltm" if selected_index == ADDITIVE_INDEX else "use_nonadditive"
    return {
        **base_context(row),
        "comparator": comparator,
        "selected_decision": selected_decision,
        "predicted_rule": selected_rule,
        "fallback_reason": "defer_or_additive" if selected_index == ADDITIVE_INDEX else "selected",
        "attention_top1": bool(use_nonadditive_target and selected_index == target_index),
        "attention_top3": bool(use_nonadditive_target and target_index in top3),
        "decision_correct": bool(row.get("decision_target") == selected_decision),
        "selected_delta": deltas[selected_index],
        "additive_delta": deltas[ADDITIVE_INDEX],
        "selected_vs_additive_delta": deltas[selected_index] - deltas[ADDITIVE_INDEX],
        "selected_utility": utilities[selected_index],
        "additive_utility": utilities[ADDITIVE_INDEX],
        "selected_vs_additive_utility": utilities[selected_index] - utilities[ADDITIVE_INDEX],
        "selected_rule_harmful": bool(harmful[selected_index]),
        "target_delta": deltas[target_index] if 0 <= target_index < len(deltas) else 0.0,
        "top3_rules": [EXECUTABLE_RULE_IDS[index] for index in top3],
        "oracle_best_safe_rule": EXECUTABLE_RULE_IDS[oracle_index],
        "oracle_best_safe_utility": utilities[oracle_index],
        "utility_regret_to_oracle": max(0.0, utilities[oracle_index] - utilities[selected_index]),
        "safe_utility_top1": selected_index == oracle_index,
        "safe_utility_top3": oracle_index in top3,
        "matched_oracle_row": True,
    }


def dataset_records(rows: list[dict[str, Any]], comparator: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in rows:
        utilities = [finite(value) for value in row["risk_adjusted_utility_vector"]]
        safe = [parse_bool(value) for value in row["safe_rule_mask"]]
        safe_nonadditive = [parse_bool(value) for value in row["safe_nonadditive_mask"]]
        if comparator == "always_additive":
            selected_index = ADDITIVE_INDEX
            top3 = [ADDITIVE_INDEX]
        elif comparator == "always_defer_ltm":
            selected_index = ADDITIVE_INDEX
            top3 = [ADDITIVE_INDEX]
        elif comparator == "oracle_best_safe_rule":
            selected_index = oracle_best_safe_index(row)
            top3 = top_indices(utilities, allowed=safe, k=3)
        elif comparator == "oracle_best_safe_nonadditive_rule":
            selected_index = oracle_best_safe_nonadditive_index(row)
            top3 = top_indices(utilities, allowed=safe_nonadditive, k=3) or [ADDITIVE_INDEX]
        elif comparator == "oracle_defer_when_no_safe_opportunity":
            selected_index = oracle_defer_when_no_safe_opportunity_index(row)
            top3 = top_indices(utilities, allowed=safe_nonadditive, k=3) or [ADDITIVE_INDEX]
        else:
            raise ValueError(f"unknown dataset comparator {comparator}")
        record = make_record_from_dataset(row, comparator=comparator, selected_index=selected_index, top3=top3)
        if comparator == "always_defer_ltm":
            record["selected_decision"] = "defer_ltm"
            record["decision_correct"] = row.get("decision_target") == "defer_ltm"
        if comparator == "always_additive":
            record["selected_decision"] = "use_nonadditive"
            record["fallback_reason"] = "additive_rule"
            record["decision_correct"] = row.get("decision_target") == "use_nonadditive"
        records.append(record)
    return records


def variant_name(path: Path) -> str:
    name = path.name
    for suffix in ("_eval_seed61.csv", "_eval_h010.csv", ".csv"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name


def load_eval_csv(path: Path, dataset_by_checkpoint: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    comparator = variant_name(path)
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            if str(raw.get("split", "")) != "validation":
                continue
            checkpoint = str(raw.get("checkpoint_id", ""))
            dataset_row = dataset_by_checkpoint.get(checkpoint)
            top3_rules = [str(value) for value in parse_list(raw.get("top3_rules"))]
            predicted_rule = str(raw.get("predicted_rule") or ADDITIVE_RULE)
            selected_index = EXECUTABLE_RULE_IDS.index(predicted_rule) if predicted_rule in EXECUTABLE_RULE_IDS else ADDITIVE_INDEX
            if dataset_row is not None:
                context = base_context(dataset_row)
                oracle_index = oracle_best_safe_index(dataset_row)
                utilities = [finite(value) for value in dataset_row["risk_adjusted_utility_vector"]]
                oracle_rule = EXECUTABLE_RULE_IDS[oracle_index]
                oracle_utility = utilities[oracle_index]
                selected_utility = finite(raw.get("selected_utility"), utilities[selected_index])
                target_index = int(context["target_rule_index"])
            else:
                context = {
                    "split": str(raw.get("split", "")),
                    "run_id": str(raw.get("run_id", "")),
                    "checkpoint_id": checkpoint,
                    "map_name": str(raw.get("map_name", "")),
                    "agents": int(raw.get("agents", 0) or 0),
                    "seed": int(raw.get("seed", 0) or 0),
                    "iteration": int(raw.get("iteration", 0) or 0),
                    "decision_target": str(raw.get("decision_target", "")),
                    "target_rule": str(raw.get("target_rule", "")),
                    "target_rule_index": -1,
                    "defer_reason": "",
                    "has_nonadditive_opportunity": parse_bool(raw.get("has_nonadditive_opportunity")),
                    "has_high_margin_nonadditive_opportunity": parse_bool(raw.get("has_high_margin_nonadditive_opportunity")),
                    "best_safe_nonadditive_advantage": finite(raw.get("best_safe_nonadditive_advantage")),
                    "opportunity_margin": finite(raw.get("opportunity_margin"), 0.010),
                }
                oracle_rule = ""
                oracle_utility = 0.0
                selected_utility = finite(raw.get("selected_utility"))
                target_index = -1
            records.append(
                {
                    **context,
                    "comparator": comparator,
                    "selected_decision": str(raw.get("selected_decision") or ("defer_ltm" if predicted_rule == ADDITIVE_RULE else "use_nonadditive")),
                    "predicted_rule": predicted_rule,
                    "fallback_reason": str(raw.get("fallback_reason", "")),
                    "attention_top1": parse_bool(raw.get("attention_top1", raw.get("top1_correct"))),
                    "attention_top3": parse_bool(raw.get("attention_top3", raw.get("top3_correct"))),
                    "decision_correct": parse_bool(raw.get("decision_correct")),
                    "selected_delta": finite(raw.get("selected_delta", raw.get("predicted_rule_delta_ratio_vs_additive"))),
                    "additive_delta": finite(raw.get("additive_delta")),
                    "selected_vs_additive_delta": finite(raw.get("selected_vs_additive_delta", raw.get("predicted_rule_delta_ratio_vs_additive"))),
                    "selected_utility": selected_utility,
                    "additive_utility": finite(raw.get("additive_utility")),
                    "selected_vs_additive_utility": finite(raw.get("selected_vs_additive_utility")),
                    "selected_rule_harmful": parse_bool(raw.get("selected_rule_harmful", raw.get("harmful_update"))),
                    "target_delta": finite(raw.get("target_delta", raw.get("delta_ratio_best"))),
                    "top3_rules": top3_rules,
                    "oracle_best_safe_rule": oracle_rule,
                    "oracle_best_safe_utility": oracle_utility,
                    "utility_regret_to_oracle": max(0.0, oracle_utility - selected_utility) if dataset_row is not None else 0.0,
                    "safe_utility_top1": bool(dataset_row is not None and predicted_rule == oracle_rule),
                    "safe_utility_top3": bool(dataset_row is not None and oracle_rule in top3_rules),
                    "matched_oracle_row": dataset_row is not None,
                    "target_rule_index": target_index,
                }
            )
    return records


def opportunity_bucket(record: dict[str, Any]) -> str:
    if record["has_high_margin_nonadditive_opportunity"]:
        return "high_margin_nonadditive_opportunity"
    if record["has_nonadditive_opportunity"]:
        return "nonadditive_opportunity"
    return "no_nonadditive_opportunity"


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}
    use_nonadditive = [row for row in records if row["decision_target"] == "use_nonadditive"]
    high_margin = [row for row in records if row["has_high_margin_nonadditive_opportunity"]]
    captured_high_margin = [
        row
        for row in high_margin
        if row["selected_decision"] != "defer_ltm"
        and row["predicted_rule"] != ADDITIVE_RULE
        and not row["selected_rule_harmful"]
        and row["selected_vs_additive_delta"] >= row["opportunity_margin"]
    ]
    avoidable_additive_or_defer = [
        row for row in high_margin if row["selected_decision"] == "defer_ltm" or row["predicted_rule"] == ADDITIVE_RULE
    ]
    matched = [row for row in records if row.get("matched_oracle_row")]
    harmful_selected = [row for row in records if row["selected_rule_harmful"]]
    false_positive_proxy = [
        row
        for row in records
        if row["fallback_reason"] == "unsafe"
        and row["has_nonadditive_opportunity"]
        and row["best_safe_nonadditive_advantage"] >= row["opportunity_margin"]
    ]
    matched_regret = mean([row["utility_regret_to_oracle"] for row in matched]) if matched else None
    matched_safe_top1 = mean([1.0 if row["safe_utility_top1"] else 0.0 for row in matched]) if matched else None
    matched_safe_top3 = mean([1.0 if row["safe_utility_top3"] else 0.0 for row in matched]) if matched else None
    return {
        "sample_count": len(records),
        "use_nonadditive_target_count": len(use_nonadditive),
        "matched_oracle_count": len(matched),
        "rule_top1": mean([1.0 if row["attention_top1"] else 0.0 for row in use_nonadditive]),
        "rule_top3": mean([1.0 if row["attention_top3"] else 0.0 for row in use_nonadditive]),
        "safe_utility_top1": matched_safe_top1,
        "safe_utility_top3": matched_safe_top3,
        "utility_regret_to_oracle": matched_regret,
        "selected_delta": mean([row["selected_delta"] for row in records]),
        "additive_delta": mean([row["additive_delta"] for row in records]),
        "selected_vs_additive_delta": mean([row["selected_vs_additive_delta"] for row in records]),
        "selected_vs_additive_utility": mean([row["selected_vs_additive_utility"] for row in records]),
        "high_margin_nonadditive_capture": safe_div(len(captured_high_margin), len(high_margin)),
        "avoidable_additive_or_defer": safe_div(len(avoidable_additive_or_defer), len(high_margin)),
        "harmful_false_negative_selected_count": len(harmful_selected),
        "harmful_false_negative_selected_rate": safe_div(len(harmful_selected), len(records)),
        "harmful_false_positive_proxy_count": len(false_positive_proxy),
        "harmful_false_positive_proxy_rate": safe_div(len(false_positive_proxy), len(records)),
        "decision_accuracy": mean([1.0 if row["decision_correct"] else 0.0 for row in records]),
        "selected_rule_distribution": dict(sorted(Counter(row["predicted_rule"] for row in records).items())),
        "decision_distribution": dict(sorted(Counter(row["selected_decision"] for row in records).items())),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def grouped_rows(records_by_comparator: dict[str, list[dict[str, Any]]], group_keys: list[str]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for comparator, records in sorted(records_by_comparator.items()):
        buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            key_values = []
            for key in group_keys:
                if key == "opportunity_bucket":
                    key_values.append(opportunity_bucket(record))
                else:
                    key_values.append(record.get(key, ""))
            buckets[tuple(key_values)].append(record)
        for key_values, values in sorted(buckets.items()):
            summary = summarize(values)
            row = {"comparator": comparator}
            row.update({key: value for key, value in zip(group_keys, key_values)})
            row.update(summary)
            output.append(row)
    return output


def hardcase_row(record: dict[str, Any], case_type: str) -> dict[str, Any]:
    return {
        "schema_version": "phase4f_repair5b_hardcase_replay_v1",
        "case_type": case_type,
        "checkpoint_id": str(record.get("checkpoint_id", "")),
        "comparator": str(record.get("comparator", "")),
        "split": str(record.get("split", "")),
        "run_id": str(record.get("run_id", "")),
        "map_name": str(record.get("map_name", "")),
        "agents": int(record.get("agents", 0) or 0),
        "seed": int(record.get("seed", 0) or 0),
        "iteration": int(record.get("iteration", 0) or 0),
        "decision_target": str(record.get("decision_target", "")),
        "target_rule": str(record.get("target_rule", "")),
        "predicted_rule": str(record.get("predicted_rule", "")),
        "fallback_reason": str(record.get("fallback_reason", "")),
        "selected_vs_additive_delta": finite(record.get("selected_vs_additive_delta")),
        "utility_regret_to_oracle": finite(record.get("utility_regret_to_oracle")),
        "has_high_margin_nonadditive_opportunity": bool(record.get("has_high_margin_nonadditive_opportunity")),
        "best_safe_nonadditive_advantage": finite(record.get("best_safe_nonadditive_advantage")),
    }


def collect_hardcases(
    records_by_comparator: dict[str, list[dict[str, Any]]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    excluded = {
        "always_additive",
        "always_defer_ltm",
        "oracle_best_safe_rule",
        "oracle_best_safe_nonadditive_rule",
        "oracle_defer_when_no_safe_opportunity",
    }
    for comparator, records in sorted(records_by_comparator.items()):
        if comparator in excluded or comparator.startswith("oracle_"):
            continue
        for record in records:
            if not record.get("matched_oracle_row"):
                continue
            case_types: list[str] = []
            target_rule = str(record.get("target_rule", ""))
            predicted_rule = str(record.get("predicted_rule", ""))
            if bool(record.get("selected_rule_harmful")):
                case_types.append("false_negative_harmful_selected")
            if bool(record.get("has_high_margin_nonadditive_opportunity")) and (
                record.get("selected_decision") == "defer_ltm" or predicted_rule == ADDITIVE_RULE
            ):
                case_types.append("high_margin_avoidable_defer")
            if (
                str(record.get("decision_target")) == "use_nonadditive"
                and not bool(record.get("attention_top1"))
                and bool(record.get("attention_top3"))
            ):
                case_types.append("wrong_rule_top1_but_top3_contains_target")
            if bool(record.get("has_high_margin_nonadditive_opportunity")) and not bool(record.get("safe_utility_top3")):
                case_types.append("top3_miss_high_utility")
            if (
                str(record.get("decision_target")) == "use_nonadditive"
                and target_rule != ADDITIVE_RULE
                and predicted_rule != ADDITIVE_RULE
                and target_rule in EXECUTABLE_RULE_IDS
                and predicted_rule in EXECUTABLE_RULE_IDS
                and target_rule != predicted_rule
                and rule_family(target_rule) != rule_family(predicted_rule)
            ):
                case_types.append("rule_family_confusion")
            for case_type in case_types:
                key = (str(record.get("checkpoint_id", "")), comparator, case_type)
                if key in seen:
                    continue
                seen.add(key)
                output.append(hardcase_row(record, case_type))
                if len(output) >= int(limit):
                    return output
    return output


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def collect_csv_paths(root: Path, globs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in globs:
        paths.extend(root.glob(pattern))
    return sorted(set(path for path in paths if path.exists()))


def write_report(path: Path, *, root: Path, summary: dict[str, Any], oracle_gap: list[dict[str, Any]], epsilon: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    comparisons = summary["comparisons"]
    ranked = sorted(
        (
            (name, values)
            for name, values in comparisons.items()
            if values.get("sample_count") and not name.startswith("oracle_")
        ),
        key=lambda item: (
            item[1].get("rule_top3", 0.0),
            item[1].get("high_margin_nonadditive_capture", 0.0),
            -(item[1].get("utility_regret_to_oracle") if item[1].get("utility_regret_to_oracle") is not None else 999.0),
        ),
        reverse=True,
    )
    gap_validation = next((row for row in oracle_gap if row["split"] == "validation"), oracle_gap[0] if oracle_gap else {})
    oracle_delta = float(gap_validation.get("oracle_vs_additive_mean_delta", 0.0) or 0.0)
    oracle_capture = float(gap_validation.get("oracle_high_margin_capture_possible", 0.0) or 0.0)
    if oracle_delta <= epsilon or oracle_capture < 0.40:
        decision = "static_rule_space_may_be_limiting"
    else:
        decision = "continue_hierarchical_attention_native_laur"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5B Failure Decomposition\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write(f"- repair5 eval CSVs: `{len(summary['repair5_eval_csvs'])}`\n")
        handle.write(f"- repair3 eval CSVs: `{len(summary['repair3_eval_csvs'])}`\n\n")
        handle.write("## Hard-Case Replay\n\n")
        handle.write(f"- index: `{summary.get('hardcase_index_jsonl')}`\n")
        handle.write(f"- cases: `{summary.get('hardcase_count')}`\n")
        handle.write(f"- distribution: `{summary.get('hardcase_distribution')}`\n\n")
        handle.write("## Oracle Gap\n\n")
        handle.write(f"- validation oracle_vs_additive_mean_delta: `{oracle_delta}`\n")
        handle.write(f"- validation oracle_high_margin_capture_possible: `{oracle_capture}`\n")
        handle.write(f"- decision: `{decision}`\n\n")
        handle.write("## Best Completed Comparators\n\n")
        handle.write("| comparator | top1 | top3 | recall proxy | precision proxy | high-margin capture | regret |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for name, values in ranked[:12]:
            regret = values.get("utility_regret_to_oracle")
            regret_text = f"{regret:.4f}" if regret is not None else "n/a"
            handle.write(
                f"| `{name}` | {values.get('rule_top1', 0.0):.4f} | {values.get('rule_top3', 0.0):.4f} | "
                f"{1.0 - values.get('harmful_false_negative_selected_rate', 0.0):.4f} | "
                f"{1.0 - values.get('harmful_false_positive_proxy_rate', 0.0):.4f} | "
                f"{values.get('high_margin_nonadditive_capture', 0.0):.4f} | "
                f"{regret_text} |\n"
            )
        handle.write("\n## Boundary\n\n")
        handle.write(
            "This diagnostic is offline-only. It does not lower Repair5B gates and does not allow Phase5.5 or Phase6.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--repair5-eval-csv", action="append", type=Path, default=[])
    parser.add_argument("--repair5-eval-glob", action="append", default=[])
    parser.add_argument("--repair3-eval-csv", action="append", type=Path, default=[])
    parser.add_argument("--report", type=Path, default=Path("outputs/reports/phase4f_repair5_failure_decomposition.md"))
    parser.add_argument("--summary-json", type=Path, default=Path("outputs/reports/phase4f_repair5_failure_decomposition.json"))
    parser.add_argument("--by-rule-csv", type=Path, default=Path("outputs/tables/phase4f_repair5_failure_by_rule.csv"))
    parser.add_argument("--by-map-csv", type=Path, default=Path("outputs/tables/phase4f_repair5_failure_by_map.csv"))
    parser.add_argument("--by-opportunity-csv", type=Path, default=Path("outputs/tables/phase4f_repair5_failure_by_opportunity.csv"))
    parser.add_argument("--oracle-gap-csv", type=Path, default=Path("outputs/tables/phase4f_repair5_oracle_gap.csv"))
    parser.add_argument(
        "--hardcase-index-jsonl",
        type=Path,
        default=Path("artifacts/teacher/laur/repair5_hardcase_index.jsonl"),
    )
    parser.add_argument("--hardcase-limit", type=int, default=5000)
    parser.add_argument("--small-epsilon", type=float, default=0.001)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_existing(args.dataset, root) if args.dataset else default_dataset(root)
    rows = read_jsonl(dataset_path)
    dataset_by_checkpoint = {row_key(row): row for row in rows}
    validation_rows = [row for row in rows if row.get("split") == "validation"]
    rows_for_oracle = validation_rows or rows

    repair5_paths = [resolve_existing(path, root) for path in args.repair5_eval_csv]
    repair5_globs = args.repair5_eval_glob or DEFAULT_REPAIR5_CSV_GLOBS
    repair5_paths.extend(collect_csv_paths(root, repair5_globs))
    repair5_paths = sorted(set(repair5_paths))

    repair3_paths = [resolve_existing(path, root) for path in args.repair3_eval_csv]
    if not repair3_paths:
        repair3_paths.extend(collect_csv_paths(root, DEFAULT_REPAIR3_CSV_GLOBS))
    repair3_paths = sorted(set(repair3_paths))

    records_by_comparator: dict[str, list[dict[str, Any]]] = {}
    for comparator in [
        "always_additive",
        "always_defer_ltm",
        "oracle_best_safe_rule",
        "oracle_best_safe_nonadditive_rule",
        "oracle_defer_when_no_safe_opportunity",
    ]:
        records_by_comparator[comparator] = dataset_records(rows_for_oracle, comparator)

    for path in repair5_paths:
        records = load_eval_csv(path, dataset_by_checkpoint)
        if records:
            records_by_comparator[variant_name(path)] = records
    for path in repair3_paths:
        records = load_eval_csv(path, dataset_by_checkpoint)
        if records:
            records_by_comparator[variant_name(path)] = records

    comparison_summary = {name: summarize(records) for name, records in sorted(records_by_comparator.items())}

    oracle_gap_rows: list[dict[str, Any]] = []
    for split in ["validation", "all"]:
        split_rows = rows_for_oracle if split == "validation" else rows
        additive = dataset_records(split_rows, "always_additive")
        oracle = dataset_records(split_rows, "oracle_best_safe_rule")
        oracle_nonadditive = dataset_records(split_rows, "oracle_best_safe_nonadditive_rule")
        additive_summary = summarize(additive)
        oracle_summary = summarize(oracle)
        oracle_nonadditive_summary = summarize(oracle_nonadditive)
        oracle_gap_rows.append(
            {
                "split": split,
                "sample_count": len(split_rows),
                "additive_mean_delta": additive_summary.get("selected_delta", 0.0),
                "oracle_best_safe_rule_mean_delta": mean([row["selected_delta"] for row in oracle]),
                "oracle_vs_additive_mean_delta": oracle_summary.get("selected_vs_additive_delta", 0.0),
                "oracle_best_safe_nonadditive_vs_additive_mean_delta": oracle_nonadditive_summary.get(
                    "selected_vs_additive_delta", 0.0
                ),
                "oracle_high_margin_capture_possible": oracle_summary.get("high_margin_nonadditive_capture", 0.0),
                "oracle_nonadditive_high_margin_capture_possible": oracle_nonadditive_summary.get(
                    "high_margin_nonadditive_capture", 0.0
                ),
                "oracle_harmful_rate": oracle_summary.get("harmful_false_negative_selected_rate", 0.0),
                "oracle_nonadditive_harmful_rate": oracle_nonadditive_summary.get(
                    "harmful_false_negative_selected_rate", 0.0
                ),
            }
        )

    by_rule = grouped_rows(records_by_comparator, ["target_rule"])
    by_map = grouped_rows(records_by_comparator, ["map_name", "agents"])
    by_opportunity = grouped_rows(records_by_comparator, ["opportunity_bucket", "decision_target"])
    hardcases = collect_hardcases(records_by_comparator, limit=int(args.hardcase_limit))

    table_fields = [
        "comparator",
        "target_rule",
        "map_name",
        "agents",
        "opportunity_bucket",
        "decision_target",
        "sample_count",
        "use_nonadditive_target_count",
        "matched_oracle_count",
        "rule_top1",
        "rule_top3",
        "safe_utility_top1",
        "safe_utility_top3",
        "utility_regret_to_oracle",
        "selected_delta",
        "additive_delta",
        "selected_vs_additive_delta",
        "selected_vs_additive_utility",
        "high_margin_nonadditive_capture",
        "avoidable_additive_or_defer",
        "harmful_false_negative_selected_count",
        "harmful_false_negative_selected_rate",
        "harmful_false_positive_proxy_count",
        "harmful_false_positive_proxy_rate",
        "decision_accuracy",
    ]
    write_csv(root / args.by_rule_csv, by_rule, table_fields)
    write_csv(root / args.by_map_csv, by_map, table_fields)
    write_csv(root / args.by_opportunity_csv, by_opportunity, table_fields)
    write_csv(
        root / args.oracle_gap_csv,
        oracle_gap_rows,
        [
            "split",
            "sample_count",
            "additive_mean_delta",
            "oracle_best_safe_rule_mean_delta",
            "oracle_vs_additive_mean_delta",
            "oracle_best_safe_nonadditive_vs_additive_mean_delta",
            "oracle_high_margin_capture_possible",
            "oracle_nonadditive_high_margin_capture_possible",
            "oracle_harmful_rate",
            "oracle_nonadditive_harmful_rate",
        ],
    )
    write_jsonl(root / args.hardcase_index_jsonl, hardcases)

    summary = {
        "schema_version": "phase4f_repair5b_failure_decomposition_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "dataset": str(dataset_path),
        "sample_count": len(rows),
        "validation_sample_count": len(rows_for_oracle),
        "repair5_eval_csvs": [str(path) for path in repair5_paths],
        "repair3_eval_csvs": [str(path) for path in repair3_paths],
        "hardcase_index_jsonl": str(root / args.hardcase_index_jsonl),
        "hardcase_count": len(hardcases),
        "hardcase_distribution": dict(sorted(Counter(row["case_type"] for row in hardcases).items())),
        "comparisons": comparison_summary,
        "oracle_gap": oracle_gap_rows,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary_path = root / args.summary_json
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_report(root / args.report, root=root, summary=summary, oracle_gap=oracle_gap_rows, epsilon=args.small_epsilon)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
