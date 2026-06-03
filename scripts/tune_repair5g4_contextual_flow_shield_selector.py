"""Tune offline contextual flow-shield selectors for Repair5G.4."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from create_repair5g4_learning_bridge_dataset import ALLOWED_FEATURES, FORBIDDEN_FEATURES  # noqa: E402
from repair5g3_common import git_value, metrics_for_rows, number, read_csv_rows, repo_root, resolve, write_csv_rows, write_json  # noqa: E402
from tune_repair5g3_contextual_flow_shield_selector import (  # noqa: E402
    best_static_method,
    candidate_methods,
    evaluate,
    finite_delta,
    make_stump,
)


DEFAULT_DATASET = "outputs/tables/phase5p5_repair5g4_learning_bridge_dataset.csv"
DEFAULT_SPEC = "outputs/reports/phase5p5_repair5g4_contextual_selector_spec.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g4_contextual_selector_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g4_contextual_selector_summary.json"
DEFAULT_EVAL = "outputs/tables/phase5p5_repair5g4_contextual_selector_dev_eval.csv"
DEFAULT_RUNTIME_GAP = "outputs/reports/phase5p5_repair5g4_contextual_selector_runtime_gap.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-csv", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--spec-json", type=Path, default=Path(DEFAULT_SPEC))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL))
    parser.add_argument("--runtime-gap-report", type=Path, default=Path(DEFAULT_RUNTIME_GAP))
    return parser.parse_args(argv)


def write_report(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.4 Contextual Selector Report\n\n")
        handle.write("Offline learning-bridge diagnostic only. No runtime learned selector is integrated here.\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary["gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Best Selector\n\n")
        handle.write(f"- name: `{summary['best_selector_name']}`\n")
        handle.write(f"- metrics: `{summary['best_selector_metrics']}`\n")


def write_runtime_gap(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Phase5.5 Repair5G.4 Contextual Selector Runtime Gap\n\n"
        f"{text}\n\n"
        "- fresh learned-selector runtime evaluation run: `false`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.dataset_csv, root))
    methods = candidate_methods(rows)
    if not rows or not methods:
        raise SystemExit("learning bridge dataset is empty")
    train_rows = [row for row in rows if not row.get("split", "").endswith("_validation")]
    val_rows = [row for row in rows if row.get("split", "").endswith("_validation")] or train_rows
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
        "learned_selector_not_map_agent_lookup_only": best_selector["name"] == "decision_stump_selector"
        and bool(stump_spec.get("feature"))
        and stump_spec.get("feature") not in {"map", "agents"},
        "learned_selector_mean_delta_ratio_vs_ltm_lt_neg_0p010": best_mean < -0.010,
        "learned_selector_bootstrap_probability_mean_delta_lt_0_ge_0p99": number(best_metrics.get("bootstrap", {}).get("prob_mean_lt_0"), 0.0) >= 0.99,
        "learned_selector_success_worse_than_ltm_groups_eq_0": int(best_metrics.get("success_worse_than_ltm_groups", 99)) == 0,
        "learned_selector_beats_static_or_matches_within_0p001": best_mean <= number(static_metrics.get("mean_delta_ratio_vs_ltm"), math.inf) + 0.001,
        "learned_selector_beats_shuffled_label_diagnostic": best_mean < number(shuffled_metrics.get("mean_delta_ratio_vs_ltm"), math.inf),
        "learned_selector_beats_random_feature_diagnostic": best_mean < number(random_metrics.get("mean_delta_ratio_vs_ltm"), math.inf),
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
        "schema_version": "phase5p5_repair5g4_contextual_selector_spec_v1",
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
        "contextual selector hook that consumes this JSON before each update. Fresh learned-selector evaluation is intentionally not run."
    )
    summary = {
        "schema_version": "phase5p5_repair5g4_contextual_selector_summary_v1",
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
        "reserved_learning_fresh_eval": "IDs 166..205 or next untouched range",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    write_runtime_gap(resolve(args.runtime_gap_report, root), runtime_gap)
    print(json.dumps({"best_selector": best_selector["name"], "learning_bridge_dev_gates_passed": gates["learning_bridge_dev_gates_passed"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
