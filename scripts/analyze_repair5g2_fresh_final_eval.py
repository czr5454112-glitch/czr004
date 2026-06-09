"""Analyze Repair5G.2 fresh-final evaluation and write the decision report."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import (  # noqa: E402
    G2_RANDOM_DIAGNOSTIC,
    G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC,
    G2_SHUFFLED_GOAL_DIAGNOSTIC,
    bootstrap_summary,
    dirty_state,
    metrics_for_long_rows,
    number,
    read_csv_rows,
    rel,
    repo_root,
    resolve,
)


DEFAULT_FINAL_PAIRED = "outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv"
DEFAULT_FINAL_SUMMARY = "outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json"
DEFAULT_SELECTOR_SUMMARY = "outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json"
DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g2_fresh_final_eval_audit.md"
DEFAULT_DECISION = "outputs/reports/phase5p5_repair5g2_decision.md"
DEFAULT_DECISION_JSON = "outputs/reports/phase5p5_repair5g2_decision_summary.json"

SELECTED_METHOD = "repair5g2_frozen_static_or_selector"


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_paired(row: dict[str, str]) -> dict[str, Any]:
    candidate = row.get("candidate_id") or row.get("contender_method") or row.get("method") or ""
    delta = row.get("delta_ratio_vs_ltm") or row.get("delta_ratio") or "0"
    return {
        "map": row.get("map", ""),
        "agents": int(number(row.get("agents"), 0)),
        "seed": int(number(row.get("seed"), 0)),
        "candidate_id": candidate,
        "delta_ratio_vs_ltm": number(delta, 0.0),
        "success": str(row.get("success", row.get("contender_success", "true"))).lower() in {"true", "1", "yes"},
    }


def rows_for(path: Path, candidate: str) -> list[dict[str, Any]]:
    return [row for row in [normalize_paired(item) for item in read_csv_rows(path)] if row["candidate_id"] == candidate]


def diagnostic_metrics(path: Path) -> dict[str, Any]:
    rows = [
        row
        for row in [normalize_paired(item) for item in read_csv_rows(path)]
        if row["candidate_id"] in {G2_RANDOM_DIAGNOSTIC, G2_SHUFFLED_GOAL_DIAGNOSTIC, G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC}
    ]
    grouped: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for row in rows:
        grouped[(row["map"], row["agents"], row["seed"], row["candidate_id"])] = row
    by_name: dict[str, dict[str, Any]] = {}
    for name in [G2_RANDOM_DIAGNOSTIC, G2_SHUFFLED_GOAL_DIAGNOSTIC, G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC]:
        by_name[name] = metrics_for_long_rows([row for row in rows if row["candidate_id"] == name])
    return by_name


def write_audit(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Fresh Final Audit\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- decision: `{summary['decision']}`\n")
        handle.write(f"- final_gates_passed: `{summary['final_gates_passed']}`\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary["final_gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Decision\n\n")
        handle.write(f"Decision: `{summary['decision']}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- no learned actions: `true`\n")
        handle.write("- no learned restart: `true`\n")
        handle.write("- no LaCAM*/PIBT semantic change: `true`\n\n")
        handle.write("## Interpretation\n\n")
        handle.write(summary["interpretation"] + "\n\n")
        handle.write("## AAAI-Style Story\n\n")
        handle.write(summary["aaai_style_story"] + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-paired-csv", type=Path, default=Path(DEFAULT_FINAL_PAIRED))
    parser.add_argument("--final-summary-json", type=Path, default=Path(DEFAULT_FINAL_SUMMARY))
    parser.add_argument("--selector-summary-json", type=Path, default=Path(DEFAULT_SELECTOR_SUMMARY))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--decision-report", type=Path, default=Path(DEFAULT_DECISION))
    parser.add_argument("--decision-summary-json", type=Path, default=Path(DEFAULT_DECISION_JSON))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    selector_summary_path = resolve(args.selector_summary_json, root)
    final_summary_path = resolve(args.final_summary_json, root)
    final_paired = resolve(args.final_paired_csv, root)
    frozen_spec_path = resolve(args.frozen_selector_spec_json, root)
    selector_summary = load_json(selector_summary_path)
    final_summary = load_json(final_summary_path)
    frozen_spec = load_json(frozen_spec_path)
    dev_passed = bool(selector_summary.get("development_gates", {}).get("development_gates_passed"))
    if not dev_passed:
        decision = "selector_protocol_failed_dev"
        final_gates: dict[str, Any] = {
            "development_gates_passed": False,
            "fresh_final_not_run": not final_paired.exists(),
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        }
        final_gates_passed = False
        selected_metrics = {}
        diagnostics = {}
        interpretation = "Development selector gates failed, so fresh final validation is intentionally blocked."
        story = "G2 does not yet support the goal-aware UpdateLTM story beyond G1 diagnostic headroom."
    elif not final_paired.exists() or not final_summary:
        decision = "selector_protocol_failed_dev"
        final_gates = {
            "development_gates_passed": True,
            "fresh_final_available": False,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        }
        final_gates_passed = False
        selected_metrics = {}
        diagnostics = {}
        interpretation = "Development gates passed, but fresh final evaluation has not been run yet."
        story = "The AAAI-style story remains unresolved until untouched final IDs are evaluated."
    else:
        selected_rows = rows_for(final_paired, SELECTED_METHOD)
        selected_metrics = metrics_for_long_rows(selected_rows)
        diagnostics = diagnostic_metrics(final_paired)
        selected_mean = number(selected_metrics.get("mean_delta_ratio_vs_ltm"), math.inf)
        random_mean = number(diagnostics.get(G2_RANDOM_DIAGNOSTIC, {}).get("mean_delta_ratio_vs_ltm"), math.inf)
        shuffled_mean = min(
            number(diagnostics.get(G2_SHUFFLED_GOAL_DIAGNOSTIC, {}).get("mean_delta_ratio_vs_ltm"), math.inf),
            number(diagnostics.get(G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC, {}).get("mean_delta_ratio_vs_ltm"), math.inf),
        )
        protocol_gates = final_summary.get("gates", {})
        final_gates = {
            "full_expected_rows": bool(protocol_gates.get("full_expected_rows")),
            "missing_rows_zero": bool(protocol_gates.get("missing_rows_zero")),
            "schema_errors_zero": bool(protocol_gates.get("schema_errors_zero")),
            "final_ids_not_used_in_tuning": bool(protocol_gates.get("final_ids_not_used_in_tuning")) and frozen_spec.get("final_ids_used_for_tuning") is False,
            "additive_parity_exact": bool(protocol_gates.get("additive_parity_exact")),
            "laur_disable_parity_exact": bool(protocol_gates.get("laur_disable_parity_exact")),
            "laur_force_additive_direct_parity_exact": bool(protocol_gates.get("laur_force_additive_direct_parity_exact")),
            "dual_additive_parity_exact": bool(protocol_gates.get("dual_additive_parity_exact")),
            "cost_bounds_respected": bool(protocol_gates.get("cost_bounds_respected")),
            "selected_method_better_gt_worse": int(selected_metrics.get("better", 0)) > int(selected_metrics.get("worse", 0)),
            "selected_method_mean_delta_ratio_vs_ltm_lt_0": selected_mean < 0.0,
            "selected_method_bootstrap_probability_mean_delta_lt_0_ge_0p95": number(selected_metrics.get("bootstrap", {}).get("prob_mean_lt_0"), 0.0) >= 0.95,
            "selected_method_ratio_worse_than_ltm_groups_le_1": int(selected_metrics.get("ratio_worse_than_ltm_groups", 99)) <= 1,
            "selected_method_success_worse_than_ltm_groups_eq_0": int(selected_metrics.get("success_worse_than_ltm_groups", 99)) == 0,
            "selected_method_beats_random_diagnostic": selected_mean < random_mean,
            "selected_method_beats_shuffled_diagnostic": selected_mean < shuffled_mean,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        }
        semantic_gates = [
            "additive_parity_exact",
            "laur_disable_parity_exact",
            "laur_force_additive_direct_parity_exact",
            "dual_additive_parity_exact",
            "cost_bounds_respected",
        ]
        semantic_failure = any(not final_gates[key] for key in semantic_gates)
        final_gates_passed = all(
            bool(value) for key, value in final_gates.items() if key not in {"phase5p5_allowed", "phase6_allowed"}
        )
        if final_gates_passed:
            decision = "continue_repair5g3_broader_validation"
            interpretation = "Fresh final IDs support the frozen flow-shield selector. Continue with broader G3 validation on new IDs/time budgets."
            story = "G2 strengthens the story that goal-aware flow-shielded UpdateLTM dynamics can improve closed-loop guidance without action or restart learning."
        elif semantic_failure:
            decision = "stop_repair5g_or_return_to_representation_design"
            interpretation = "Fresh final evaluation exposed parity, cost, or semantic-gate failure. Do not interpret performance."
            story = "The AAAI-style story is blocked by implementation/semantic safety, not by effect size."
        else:
            decision = "selector_failed_fresh_final"
            interpretation = "The frozen selector did not pass fresh final performance/diagnostic gates. Do not retune on IDs 46..65."
            story = "G2 does not yet provide fresh holdout support for the goal-aware UpdateLTM claim."
    summary = {
        "schema_version": "phase5p5_repair5g2_decision_summary_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "selector_summary_json": rel(selector_summary_path, root),
        "final_summary_json": rel(final_summary_path, root),
        "frozen_selector_spec_json": rel(frozen_spec_path, root),
        "decision": decision,
        "final_gates": final_gates,
        "final_gates_passed": final_gates_passed,
        "selected_final_metrics": selected_metrics,
        "diagnostic_metrics": diagnostics,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "no_learned_actions": True,
        "no_learned_restart": True,
        "no_lacam_pibt_semantic_change": True,
        "interpretation": interpretation,
        "aaai_style_story": story,
    }
    decision_json = resolve(args.decision_summary_json, root)
    decision_json.parent.mkdir(parents=True, exist_ok=True)
    decision_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_audit(resolve(args.audit_report, root), summary)
    write_decision(resolve(args.decision_report, root), summary)
    print(json.dumps({"decision": decision, "final_gates_passed": final_gates_passed}))
    return 0 if decision in {"continue_repair5g3_broader_validation", "selector_protocol_failed_dev", "selector_failed_fresh_final"} else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
