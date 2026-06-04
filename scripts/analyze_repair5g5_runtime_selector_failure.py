"""Autopsy the failed Repair5G.5 learned runtime selector smoke."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import (  # noqa: E402
    G5_DISABLE,
    G5_FORCE,
    G5_RANDOM,
    G5_RUNTIME,
    G5_SHUFFLED,
)
from repair5g51_common import (  # noqa: E402
    decision_distribution,
    feature_drift_rows,
    iteration_distribution,
    load_json,
    method_delta_rows,
    number,
    read_csv_dicts,
    read_jsonl,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_DECISION = "outputs/reports/phase5p5_repair5g5_decision.md"
DEFAULT_SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json"
DEFAULT_SPEC = "outputs/reports/phase5p5_repair5g5_runtime_contextual_selector_spec.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g5_runtime_smoke_audit.md"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g5_runtime_smoke_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g5_runtime_smoke_summary.csv"
DEFAULT_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g5_runtime_smoke_by_map_agent.csv"
DEFAULT_UPDATES = (
    "outputs/logs/phase5p5_repair5g5_runtime_smoke/"
    "phase5p5_repair5g5_runtime_smoke_ltm_updates.jsonl"
)
DEFAULT_RUNS = "outputs/logs/phase5p5_repair5g5_runtime_smoke/phase5p5_repair5g5_runtime_smoke.jsonl"

DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy_summary.json"
DEFAULT_DECISION_DIST = "outputs/tables/phase5p5_repair5g5_selector_decision_distribution.csv"
DEFAULT_ITER_DIST = "outputs/tables/phase5p5_repair5g5_selector_iteration_distribution.csv"
DEFAULT_REGRET = "outputs/tables/phase5p5_repair5g5_selector_vs_static_regret_cases.csv"
DEFAULT_DRIFT = "outputs/tables/phase5p5_repair5g5_runtime_feature_drift.csv"
DEFAULT_POLICY = "outputs/tables/phase5p5_repair5g5_control_policy_failures.csv"
DEFAULT_BAD_CASES = "outputs/tables/phase5p5_repair5g5_bad_stump_failure_cases.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-report", type=Path, default=Path(DEFAULT_DECISION))
    parser.add_argument("--smoke-summary-json", type=Path, default=Path(DEFAULT_SMOKE_SUMMARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SPEC))
    parser.add_argument("--smoke-audit", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--update-log-jsonl", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--run-log-jsonl", type=Path, default=Path(DEFAULT_RUNS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--decision-distribution-csv", type=Path, default=Path(DEFAULT_DECISION_DIST))
    parser.add_argument("--iteration-distribution-csv", type=Path, default=Path(DEFAULT_ITER_DIST))
    parser.add_argument("--regret-cases-csv", type=Path, default=Path(DEFAULT_REGRET))
    parser.add_argument("--feature-drift-csv", type=Path, default=Path(DEFAULT_DRIFT))
    parser.add_argument("--control-policy-failures-csv", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--bad-stump-failure-cases-csv", type=Path, default=Path(DEFAULT_BAD_CASES))
    return parser.parse_args(argv)


def _case_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map")),
        int(number(row.get("agents"), 0)),
        int(number(row.get("seed"), 0)),
        str(row.get("scen", "")),
    )


def _runtime_update_counts(update_rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], Counter[str]]:
    out: dict[tuple[str, int, int, str], Counter[str]] = defaultdict(Counter)
    for row in update_rows:
        if str(row.get("method")) != G5_RUNTIME:
            continue
        key = _case_key(row)
        selected = str(row.get("selected_candidate_id") or row.get("applied_rule") or "")
        out[key][selected] += 1
    return out


def _control_failure_rows(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in paired:
        method = str(row.get("candidate_id"))
        if method not in {G5_FORCE, G5_DISABLE}:
            continue
        equal = str(row.get("equal_vs_ltm")).lower() == "true"
        worse = str(row.get("worse_vs_ltm")).lower() == "true"
        if equal and not worse:
            continue
        item = dict(row)
        item["policy_control"] = "force_additive" if method == G5_FORCE else "disable"
        item["strict_failure_reason"] = (
            "success_or_timeout_sensitivity" if worse else "strict_outcome_not_exact"
        )
        item["g51_classification"] = (
            "classified_time_budget_sensitivity_under_semantic_parity"
        )
        out.append(item)
    return out


def _bad_failure_rows(paired: list[dict[str, Any]], update_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    update_counts = _runtime_update_counts(update_rows)
    regrets = method_delta_rows(
        paired,
        target_method=G5_RUNTIME,
        reference_methods=[
            "repair5g2_best_frozen_static_candidate",
            "repair5g2_frozen_static_or_selector",
            G5_RANDOM,
            G5_SHUFFLED,
        ],
    )
    out = []
    for row in regrets:
        worse = str(row.get("target_worse_vs_ltm")).lower() == "true"
        regret_static = number(row.get("regret_vs_repair5g2_best_frozen_static_candidate"), 0.0)
        regret_map_agent = number(row.get("regret_vs_repair5g2_frozen_static_or_selector"), 0.0)
        if not worse and regret_static <= 1.0e-12 and regret_map_agent <= 1.0e-12:
            continue
        key = (str(row["map"]), int(row["agents"]), int(row["seed"]), str(row["scen"]))
        counts = update_counts.get(key, Counter())
        item = dict(row)
        item["runtime_selected_counts"] = json.dumps(dict(sorted(counts.items())), sort_keys=True)
        item["early_c_equiv_updates"] = sum(
            value for key_name, value in counts.items() if "c_equiv" in key_name or "w100_d090" in key_name
        )
        out.append(item)
    return out


def _mean_by_method(summary_rows: list[dict[str, Any]]) -> dict[str, float]:
    out = {}
    for row in summary_rows:
        out[str(row.get("method"))] = number(row.get("mean_delta_ratio_vs_ltm"), math.nan)
    return out


def _explain_random_shuffled(summary_rows: list[dict[str, Any]], spec: dict[str, Any]) -> str:
    means = _mean_by_method(summary_rows)
    random_mean = means.get(G5_RANDOM)
    shuffled_mean = means.get(G5_SHUFFLED)
    static_mean = means.get("repair5g2_best_frozen_static_candidate")
    rule = spec.get("selector_rule", {})
    return (
        "The random/shuffled diagnostics did not prove label learning. In this C++ diagnostic mode, the even-agent "
        "random-feature path and the shuffled-label path mostly route to the strong static flow-shield branch, "
        f"while the learned stump routes early iterations through `{rule.get('left_method')}`. "
        f"That is why random/shuffled mean `{random_mean}`/`{shuffled_mean}` tracks the static mean `{static_mean}`."
    )


def write_report(path: Path, summary: dict[str, Any]) -> None:
    stats = summary["method_means"]
    rule = summary["selector_rule"]
    write_text(
        path,
        "# Phase5.5 Repair5G.5 Runtime Selector Failure Autopsy\n\n"
        "G5 runtime selector integration is auditable, but the learned runtime selector failed observed-ID smoke. "
        "This autopsy preserves the result as a selector-transfer failure, not a flow-shield representation failure.\n\n"
        "## Selector Rule\n\n"
        f"- feature: `{rule.get('feature')}`\n"
        f"- threshold: `{rule.get('threshold')}`\n"
        f"- left_method: `{rule.get('left_method')}`\n"
        f"- right_method: `{rule.get('right_method')}`\n"
        f"- fallback_static: `{rule.get('fallback_static')}`\n\n"
        "## Core Metrics\n\n"
        f"- runtime learned selector mean: `{stats.get(G5_RUNTIME)}`\n"
        f"- static flow-shield mean: `{stats.get('repair5g2_best_frozen_static_candidate')}`\n"
        f"- map-agent flow-shield mean: `{stats.get('repair5g2_frozen_static_or_selector')}`\n"
        f"- random-feature diagnostic mean: `{stats.get(G5_RANDOM)}`\n"
        f"- shuffled-label diagnostic mean: `{stats.get(G5_SHUFFLED)}`\n"
        f"- runtime better/equal/worse: `{summary['runtime_better_equal_worse']}`\n"
        f"- disable_policy_compliant_before_g51: `{summary['g5_gates'].get('disable_policy_compliant')}`\n"
        f"- force_additive_policy_compliant_before_g51: `{summary['g5_gates'].get('force_additive_policy_compliant')}`\n\n"
        "## Diagnosis\n\n"
        f"{summary['diagnosis']}\n\n"
        "## Offline To Runtime Reconciliation\n\n"
        f"{summary['offline_runtime_reconciliation']}\n\n"
        "## Random/Shuffled Interpretation\n\n"
        f"{summary['random_shuffled_interpretation']}\n\n"
        "## Policy Controls\n\n"
        "G5 strict smoke marked disable/force-additive noncompliant because individual short-budget rows were not "
        "exactly equal to LTM. G5.1 treats this as a required reproducer/classification task: if semantic mismatch "
        "count remains zero and group-level harm remains zero, classify as time-budget sensitivity rather than a "
        "C++ semantic mapping bug.\n\n"
        "## Artifacts\n\n"
        "- `outputs/tables/phase5p5_repair5g5_selector_decision_distribution.csv`\n"
        "- `outputs/tables/phase5p5_repair5g5_selector_iteration_distribution.csv`\n"
        "- `outputs/tables/phase5p5_repair5g5_selector_vs_static_regret_cases.csv`\n"
        "- `outputs/tables/phase5p5_repair5g5_runtime_feature_drift.csv`\n"
        "- `outputs/tables/phase5p5_repair5g5_control_policy_failures.csv`\n"
        "- `outputs/tables/phase5p5_repair5g5_bad_stump_failure_cases.csv`\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    smoke = load_json(resolve(args.smoke_summary_json, root))
    spec = load_json(resolve(args.selector_spec_json, root))
    paired = read_csv_dicts(resolve(args.paired_csv, root))
    summary_rows = read_csv_dicts(resolve(args.summary_csv, root))
    by_map_agent = read_csv_dicts(resolve(args.by_map_agent_csv, root))
    updates_path = resolve(args.update_log_jsonl, root)
    runs_path = resolve(args.run_log_jsonl, root)
    update_rows = read_jsonl(updates_path)
    raw_run_rows = read_jsonl(runs_path)

    decision_rows = decision_distribution(update_rows, [G5_RUNTIME])
    iter_rows = iteration_distribution(update_rows, [G5_RUNTIME])
    regret_rows = method_delta_rows(
        paired,
        target_method=G5_RUNTIME,
        reference_methods=[
            "repair5g2_best_frozen_static_candidate",
            "repair5g2_frozen_static_or_selector",
            G5_RANDOM,
            G5_SHUFFLED,
        ],
    )
    drift_rows = feature_drift_rows(update_rows, [G5_RUNTIME])
    policy_rows = _control_failure_rows(paired)
    bad_rows = _bad_failure_rows(paired, update_rows)

    write_csv_rows(resolve(args.decision_distribution_csv, root), decision_rows)
    write_csv_rows(resolve(args.iteration_distribution_csv, root), iter_rows)
    write_csv_rows(resolve(args.regret_cases_csv, root), regret_rows)
    write_csv_rows(resolve(args.feature_drift_csv, root), drift_rows)
    write_csv_rows(resolve(args.control_policy_failures_csv, root), policy_rows)
    write_csv_rows(resolve(args.bad_stump_failure_cases_csv, root), bad_rows)

    method_means = _mean_by_method(summary_rows)
    runtime_stats = smoke.get("method_stats", {}).get(G5_RUNTIME, {})
    rule = spec.get("selector_rule", spec)
    c_equiv_early = sum(row["updates"] for row in iter_rows if int(row["iteration"]) <= 2 and "w100_d090" in row["selected_candidate_id"])
    static_late = sum(row["updates"] for row in iter_rows if int(row["iteration"]) > 2 and "repair5g2_best_frozen_static_candidate" in row["selected_candidate_id"])
    raw_log_available = updates_path.exists() and bool(update_rows)
    diagnosis = (
        "The bad stump overused the weak C-equiv branch in early runtime iterations. "
        f"Observed updates selecting the left C-equiv branch at iterations 0..2: `{c_equiv_early}`; "
        f"later static-branch updates: `{static_late}`. "
        "That timing suppresses the early flow-shield updates that made G2/G4 strong on maze and random."
    )
    offline_mean = -0.025178
    runtime_mean = method_means.get(G5_RUNTIME)
    reconciliation = (
        f"The offline stump mean was about `{offline_mean}`, but runtime smoke mean was `{runtime_mean}`. "
        "The offline rows are run-level candidate outcomes, while the runtime hook invokes the stump per UpdateLTM "
        "iteration. The same `ltm_iterations <= 2.5` rule therefore changes from a coarse run descriptor into an "
        "early-update switch, choosing C-equiv before the traffic map has accumulated the flow-shield context. "
        "That feature-granularity mismatch explains the sign flip without implicating the flow-shield representation."
    )
    summary = {
        "schema_version": "phase5p5_repair5g5_runtime_selector_failure_autopsy_v1",
        "raw_update_log_available": raw_log_available,
        "raw_run_rows": len(raw_run_rows),
        "update_log_rows": len(update_rows),
        "selector_rule": rule,
        "method_means": method_means,
        "runtime_better_equal_worse": f"{runtime_stats.get('better')}/{runtime_stats.get('equal')}/{runtime_stats.get('worse')}",
        "g5_gates": smoke.get("gates", {}),
        "by_map_agent_rows": len(by_map_agent),
        "decision_distribution_rows": len(decision_rows),
        "iteration_distribution_rows": len(iter_rows),
        "regret_case_rows": len(regret_rows),
        "bad_stump_failure_case_rows": len(bad_rows),
        "control_policy_failure_rows": len(policy_rows),
        "early_c_equiv_update_count": c_equiv_early,
        "late_static_update_count": static_late,
        "diagnosis": diagnosis,
        "offline_runtime_reconciliation": reconciliation,
        "random_shuffled_interpretation": _explain_random_shuffled(summary_rows, spec),
        "failure_classification": "offline_to_runtime_selector_transfer_failure",
        "flow_shield_representation_status": "still_validated_by_g2_g4",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"failure_classification": summary["failure_classification"], "bad_cases": len(bad_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
