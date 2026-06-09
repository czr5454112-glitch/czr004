"""Tune offline contextual flow-shield selectors for Repair5G.3."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import (  # noqa: E402
    bootstrap_summary,
    git_value,
    load_json,
    metrics_for_rows,
    number,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
)
from create_repair5g3_learning_bridge_dataset import ALLOWED_FEATURES, FORBIDDEN_FEATURES  # noqa: E402


DEFAULT_DATASET = "outputs/tables/phase5p5_repair5g3_learning_bridge_dataset.csv"
DEFAULT_SPEC = "outputs/reports/phase5p5_repair5g3_contextual_selector_spec.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g3_contextual_selector_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g3_contextual_selector_summary.json"
DEFAULT_EVAL = "outputs/tables/phase5p5_repair5g3_contextual_selector_dev_eval.csv"
DEFAULT_DECISION = "outputs/reports/phase5p5_repair5g3_decision.md"
DEFAULT_DECISION_JSON = "outputs/reports/phase5p5_repair5g3_decision_summary.json"
DEFAULT_BROAD = "outputs/reports/phase5p5_repair5g3_broader_validation_summary.json"
DEFAULT_STRESS = "outputs/reports/phase5p5_repair5g3_time_iteration_stress_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-csv", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--spec-json", type=Path, default=Path(DEFAULT_SPEC))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL))
    parser.add_argument("--g3-decision-report", type=Path, default=Path(DEFAULT_DECISION))
    parser.add_argument("--g3-decision-summary-json", type=Path, default=Path(DEFAULT_DECISION_JSON))
    parser.add_argument("--broader-summary-json", type=Path, default=Path(DEFAULT_BROAD))
    parser.add_argument("--stress-summary-json", type=Path, default=Path(DEFAULT_STRESS))
    return parser.parse_args(argv)


def candidate_methods(rows: list[dict[str, str]]) -> list[str]:
    methods = []
    for key in rows[0] if rows else []:
        if key.startswith("delta__"):
            methods.append(key[len("delta__") :])
    return methods


def finite_delta(row: dict[str, str], method: str) -> float:
    return number(row.get(f"delta__{method}"), math.inf)


def evaluate(rows: list[dict[str, str]], selector: Callable[[dict[str, str]], str], name: str) -> dict[str, Any]:
    selected = []
    for row in rows:
        method = selector(row)
        delta = finite_delta(row, method)
        selected.append(
            {
                "map": row.get("map", ""),
                "agents": int(float(row.get("agents", 0) or 0)),
                "seed": int(float(row.get("seed_metadata_only", 0) or 0)),
                "candidate_id": name,
                "selected_method": method,
                "delta_ratio_vs_ltm": delta if math.isfinite(delta) else None,
                "better_vs_ltm": math.isfinite(delta) and delta < -1.0e-12,
                "equal_vs_ltm": math.isfinite(delta) and abs(delta) <= 1.0e-12,
                "worse_vs_ltm": math.isfinite(delta) and delta > 1.0e-12,
            }
        )
    return {"name": name, "rows": selected, "metrics": metrics_for_rows(selected)}


def best_static_method(rows: list[dict[str, str]], methods: list[str]) -> str:
    means = []
    for method in methods:
        values = [finite_delta(row, method) for row in rows if math.isfinite(finite_delta(row, method))]
        if values:
            means.append((statistics.mean(values), method))
    return min(means)[1] if means else methods[0]


def make_stump(rows: list[dict[str, str]], methods: list[str]) -> tuple[Callable[[dict[str, str]], str], dict[str, Any]]:
    baseline = best_static_method(rows, methods)
    best = (math.inf, "", 0.0, baseline, baseline)
    for feature in ALLOWED_FEATURES:
        values = sorted({number(row.get(feature), math.nan) for row in rows if math.isfinite(number(row.get(feature), math.nan))})
        if len(values) < 2:
            continue
        thresholds = [(values[i] + values[i + 1]) / 2.0 for i in range(len(values) - 1)]
        for threshold in thresholds[:50]:
            left_rows = [row for row in rows if number(row.get(feature), -math.inf) <= threshold]
            right_rows = [row for row in rows if number(row.get(feature), -math.inf) > threshold]
            if not left_rows or not right_rows:
                continue
            left = best_static_method(left_rows, methods)
            right = best_static_method(right_rows, methods)
            values_selected = [finite_delta(row, left if number(row.get(feature), -math.inf) <= threshold else right) for row in rows]
            clean = [value for value in values_selected if math.isfinite(value)]
            if clean and statistics.mean(clean) < best[0]:
                best = (statistics.mean(clean), feature, threshold, left, right)

    def selector(row: dict[str, str]) -> str:
        _, feature, threshold, left, right = best
        if not feature:
            return baseline
        return left if number(row.get(feature), -math.inf) <= threshold else right

    return selector, {
        "type": "decision_stump",
        "feature": best[1],
        "threshold": best[2],
        "left_method": best[3],
        "right_method": best[4],
        "fallback_static": baseline,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3 Contextual Selector Report\n\n")
        handle.write("Offline learning-bridge diagnostic only. No runtime selector is integrated here.\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary["gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Best Selector\n\n")
        handle.write(f"- name: `{summary['best_selector_name']}`\n")
        handle.write(f"- metrics: `{summary['best_selector_metrics']}`\n\n")
        handle.write("## Runtime Integration Gap\n\n")
        handle.write(summary["runtime_integration_gap"] + "\n")


def write_decision(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3 Decision\n\n")
        handle.write(f"Decision: `{payload['decision']}`\n\n")
        for answer in payload["answers"]:
            handle.write(f"- {answer}\n")
        handle.write("\n## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- diagnostic_only: `true`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.dataset_csv, root))
    methods = candidate_methods(rows)
    train_rows = [row for row in rows if row.get("split") != "g3_broader_validation"]
    val_rows = [row for row in rows if row.get("split") == "g3_broader_validation"] or train_rows
    if not rows or not methods:
        raise SystemExit("learning bridge dataset is empty")
    static_method = best_static_method(train_rows, [m for m in methods if m.startswith("repair5g1_shield_")] or methods)
    all_static_method = best_static_method(train_rows, methods)
    stump_selector, stump_spec = make_stump(train_rows, methods)
    rng = random.Random(20260603)
    shuffled_labels = [row.get("best_method_label", "") for row in train_rows]
    rng.shuffle(shuffled_labels)
    shuffled_default = shuffled_labels[0] if shuffled_labels and shuffled_labels[0] in methods else all_static_method

    selectors = [
        evaluate(val_rows, lambda row, m=static_method: m, "static_top_flow_shield"),
        evaluate(val_rows, lambda row, m=all_static_method: m, "risk_capped_static_selector"),
        evaluate(val_rows, stump_selector, "decision_stump_selector"),
        evaluate(val_rows, lambda row, m=shuffled_default: m, "shuffled_label_diagnostic_selector"),
        evaluate(val_rows, lambda row: methods[int(number(row.get("agents"), 0)) % len(methods)], "random_feature_diagnostic_selector"),
    ]
    eval_rows = []
    for selector in selectors:
        for row in selector["rows"]:
            eval_rows.append({"selector": selector["name"], **row})
    write_csv_rows(resolve(args.eval_csv, root), eval_rows)
    metrics_by_name = {selector["name"]: selector["metrics"] for selector in selectors}
    best_selector = min(selectors, key=lambda item: number(item["metrics"].get("mean_delta_ratio_vs_ltm"), math.inf))
    best_metrics = best_selector["metrics"]
    static_metrics = metrics_by_name["static_top_flow_shield"]
    shuffled_metrics = metrics_by_name["shuffled_label_diagnostic_selector"]
    random_metrics = metrics_by_name["random_feature_diagnostic_selector"]
    best_mean = number(best_metrics.get("mean_delta_ratio_vs_ltm"), math.inf)
    gates = {
        "learned_selector_uses_no_forbidden_features": True,
        "learned_selector_mean_delta_ratio_vs_ltm_lt_neg_0p008": best_mean < -0.008,
        "learned_selector_bootstrap_probability_mean_delta_lt_0_ge_0p99": number(best_metrics.get("bootstrap", {}).get("prob_mean_lt_0"), 0.0) >= 0.99,
        "learned_selector_success_worse_than_ltm_groups_eq_0": int(best_metrics.get("success_worse_than_ltm_groups", 99)) == 0,
        "learned_selector_beats_static_or_matches_within_0p001": best_mean <= number(static_metrics.get("mean_delta_ratio_vs_ltm"), math.inf) + 0.001,
        "learned_selector_beats_shuffled_label_diagnostic": best_mean < number(shuffled_metrics.get("mean_delta_ratio_vs_ltm"), math.inf),
        "learned_selector_beats_random_feature_diagnostic": best_mean < number(random_metrics.get("mean_delta_ratio_vs_ltm"), math.inf),
        "learned_selector_not_map_agent_lookup_only": best_selector["name"] == "decision_stump_selector" and bool(stump_spec.get("feature")) and stump_spec.get("feature") not in {"agents"},
        "runtime_integration_feasible": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    gates["learning_bridge_dev_gates_passed"] = all(
        bool(value)
        for key, value in gates.items()
        if key not in {"runtime_integration_feasible", "phase5p5_allowed", "phase6_allowed"}
    )
    spec_payload = {
        "schema_version": "phase5p5_repair5g3_contextual_selector_spec_v1",
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "selector_name": best_selector["name"],
        "selector_spec": stump_spec if best_selector["name"] == "decision_stump_selector" else {"type": best_selector["name"], "method": static_method},
        "allowed_feature_names": ALLOWED_FEATURES,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
        "runtime_integration_feasible": False,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.spec_json, root), spec_payload)
    runtime_gap = (
        "The offline selector chooses bounded UpdateLTM/flow-shield methods, but phase1a_batch has no runtime "
        "contextual selector hook that consumes this JSON before each update. Fresh learned-selector evaluation is "
        "therefore intentionally not run."
    )
    summary = {
        "schema_version": "phase5p5_repair5g3_contextual_selector_summary_v1",
        "created_at": spec_payload["created_at"],
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dataset_rows": len(rows),
        "train_rows": len(train_rows),
        "validation_rows": len(val_rows),
        "candidate_methods": methods,
        "selector_metrics": metrics_by_name,
        "best_selector_name": best_selector["name"],
        "best_selector_metrics": best_metrics,
        "gates": gates,
        "runtime_integration_gap": runtime_gap,
        "fresh_learned_selector_eval_run": False,
        "reserved_learning_holdout": "IDs 106..125 remain preferred untouched learned-selector holdout",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)

    broad = load_json(resolve(args.broader_summary_json, root))
    stress = load_json(resolve(args.stress_summary_json, root))
    if not broad.get("gates", {}).get("protocol_gates_passed", False):
        decision = "protocol_failed"
    elif broad.get("decision_after_p4") == "flow_shield_representation_valid_selector_unclear":
        decision = "flow_shield_representation_valid_selector_unclear"
    elif gates["learning_bridge_dev_gates_passed"] and not gates["runtime_integration_feasible"]:
        decision = "continue_contextual_learning_bridge"
    else:
        decision = broad.get("decision_after_p4", "continue_contextual_learning_bridge")
    answers = [
        f"Does flow-shield survive broader new-ID validation? `{broad.get('gates', {}).get('representation_gates_passed', False)}`.",
        f"Is static flow-shield enough? `{broad.get('gates', {}).get('selector_vs_static_classification', '')}`.",
        f"Does map-agent selector add value over static? `{broad.get('gates', {}).get('selector_vs_static_classification', '')}`.",
        f"Is a learned contextual selector worth building/running? `offline_bridge={gates['learning_bridge_dev_gates_passed']}`, `runtime_integration_feasible=false`.",
        f"Is the effect stable across time/iteration budgets? `stress_protocol_passed={stress.get('gates', {}).get('stress_protocol_passed', False)}`.",
        "Observed IDs now include `1..105` if G3 broader validation completed; learning holdout `106..125` remains reserved.",
        "Recommended G4 split: formal promotion-candidate validation on the next clean range after any learned-selector holdout, preferably `126..165` if `106..125` stays reserved.",
    ]
    decision_payload = {
        "schema_version": "phase5p5_repair5g3_decision_summary_v1",
        "created_at": spec_payload["created_at"],
        "decision": decision,
        "answers": answers,
        "broader_summary": str(resolve(args.broader_summary_json, root).relative_to(root)),
        "stress_summary": str(resolve(args.stress_summary_json, root).relative_to(root)) if resolve(args.stress_summary_json, root).exists() else "",
        "contextual_selector_summary": str(resolve(args.summary_json, root).relative_to(root)),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "diagnostic_only": True,
    }
    write_json(resolve(args.g3_decision_summary_json, root), decision_payload)
    write_decision(resolve(args.g3_decision_report, root), decision_payload)
    print(json.dumps({"best_selector": best_selector["name"], "learning_bridge_dev_gates_passed": gates["learning_bridge_dev_gates_passed"], "decision": decision}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
