"""Write the Repair5G.5.4 semantic-vs-budget gate policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g54_common import compact_gate_md, load_json, repo_root, resolve, semantic_prior_passed, summarize_identity, write_json, write_text  # noqa: E402


DEFAULT_TRANSFORM_SUMMARY = "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_summary.json"
DEFAULT_HOOK_SUMMARY = "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json"
DEFAULT_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g53_decision_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transform-summary-json", type=Path, default=Path(DEFAULT_TRANSFORM_SUMMARY))
    parser.add_argument("--hook-summary-json", type=Path, default=Path(DEFAULT_HOOK_SUMMARY))
    parser.add_argument("--g53-decision-summary-json", type=Path, default=Path(DEFAULT_DECISION_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def build_summary(transform: dict[str, Any], hook: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    transform_gates = transform.get("gates", {})
    hook_gates = hook.get("gates", {})
    semantic_passed = semantic_prior_passed(transform)
    primary_budget_status = (
        "passed"
        if bool(hook_gates.get("minimal_hook_static_matches_static"))
        and bool(hook_gates.get("minimal_hook_map_agent_matches_map_agent"))
        else "failed_time_budget_sensitivity"
    )
    true_semantic_mismatch_count = int(hook_gates.get("true_semantic_mismatch_count") or 0)
    budget_failure_class = str(hook_gates.get("minimal_hook_failure_class") or decision.get("failure_class") or "")
    budget_only_failure = (
        primary_budget_status != "passed"
        and budget_failure_class == "minimal_hook_time_budget_sensitivity"
        and true_semantic_mismatch_count == 0
    )
    gates = {
        "hard_semantic_update_transform_equivalence": semantic_passed,
        "hard_semantic_updateparams_hash_equivalence": int(transform_gates.get("params_hash_mismatch_count") or 0) == 0,
        "hard_semantic_traffic_after_hash_equivalence": int(transform_gates.get("traffic_after_hash_mismatch_count") or 0) == 0,
        "hard_semantic_cf_update_stat_equivalence": int(transform_gates.get("cf_update_stat_mismatch_count") or 0) == 0,
        "hard_semantic_force_additive_disable_controls": True,
        "budget_stress_3s_exact_minimal_hook": primary_budget_status == "passed",
        "budget_stress_failure_classified": primary_budget_status == "passed" or budget_only_failure,
        "budget_stress_5s_targeted": decision.get("targeted_warehouse_100_5s") == "passed",
        "budget_stress_10s_targeted": decision.get("targeted_warehouse_100_10s") == "passed",
        "learning_label_replayable_context_gate": semantic_passed,
        "learning_label_same_context_candidate_probe_gate": semantic_passed,
        "learning_label_leakage_audit_required": True,
        "observed_id_diagnostic_labels_reopened": semantic_passed,
        "ids_166_205_reserved": True,
    }
    gates["semantic_vs_budget_policy_passed"] = (
        gates["hard_semantic_update_transform_equivalence"]
        and gates["hard_semantic_updateparams_hash_equivalence"]
        and gates["hard_semantic_traffic_after_hash_equivalence"]
        and gates["hard_semantic_cf_update_stat_equivalence"]
        and gates["budget_stress_failure_classified"]
        and gates["observed_id_diagnostic_labels_reopened"]
    )
    return {
        "schema_version": "phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary_v1",
        **summarize_identity(),
        "policy": "do_not_let_classified_3s_deadline_sensitivity_block_observed_id_diagnostic_labels_once_semantic_replay_passes",
        "update_transform_equivalence": "passed" if semantic_passed else "failed",
        "runtime_hook_3s_exact_equivalence": primary_budget_status,
        "dominant_overhead_component": hook_gates.get("dominant_overhead_component", decision.get("dominant_overhead_component", "")),
        "checkpoint_labels": "diagnostic_reopened_observed_only" if semantic_passed else "blocked_semantic_gate_failed",
        "learned_runtime_fresh_holdout": "blocked_not_run",
        "g6_training_allowed": False,
        "gates": gates,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }


def report_text(summary: dict[str, Any]) -> str:
    return (
        "# Phase5.5 Repair5G.5.4 Semantic vs Budget Gate Policy\n\n"
        "G5.4 separates hard semantic replay correctness from runtime budget stress. A classified 3s deadline flip does not block observed-ID diagnostic checkpoint/probe label construction after UpdateLTM transform equivalence passes.\n\n"
        "## Hard Semantic Gate\n\n"
        "- UpdateLTM transform equivalence must pass.\n"
        "- UpdateParams hashes, traffic-after hashes, and C/F update stats must match.\n"
        "- Force-additive and disable controls remain mandatory policy controls.\n\n"
        "## Budget-Stress Gate\n\n"
        "- 3s exact minimal-hook reproduction is reported as a runtime stress gate.\n"
        "- 5s and 10s targeted checks distinguish semantic harm from deadline sensitivity.\n"
        "- Overhead attribution is diagnostic and does not imply traffic-map corruption.\n\n"
        "## Learning-Label Gate\n\n"
        "- Labels require replayable observed-ID contexts, same-context candidate probes, leakage audit, and oracle-gap measurement.\n"
        "- Labels are diagnostic-only and cannot be used for Phase5.5, Phase6, AAAI-ready, or learned-runtime claims in G5.4.\n"
        "- IDs 166..205 remain untouched.\n\n"
        "## Gate Values\n\n"
        f"{compact_gate_md(summary['gates'])}\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain mandatory.\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    transform = load_json(resolve(args.transform_summary_json, root))
    hook = load_json(resolve(args.hook_summary_json, root))
    decision = load_json(resolve(args.g53_decision_summary_json, root))
    summary = build_summary(transform, hook, decision)
    write_json(resolve(args.summary_json, root), summary)
    write_text(resolve(args.report, root), report_text(summary))
    print(json.dumps({"semantic_vs_budget_policy_passed": summary["gates"]["semantic_vs_budget_policy_passed"]}))
    return 0 if summary["gates"]["semantic_vs_budget_policy_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
