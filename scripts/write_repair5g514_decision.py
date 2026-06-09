"""Write the final G5.14 decision report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import finite_number, read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g514_common import G514_CLOSED_CLAIMS  # noqa: E402


DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_decision_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_decision.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def read_optional(path: str) -> dict:
    target = resolve(path, repo_root())
    return read_json(target) if target.exists() else {}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    artifact = read_optional("outputs/reports/phase5p5_repair5g514_g513_artifact_verification_summary.json")
    checkpoint = read_optional("outputs/reports/phase5p5_repair5g514_existing_rich_checkpoint_artifacts_summary.json")
    rich = read_optional("outputs/reports/phase5p5_repair5g514_rich_context_features_summary.json")
    v4_matrix = read_optional("outputs/reports/phase5p5_repair5g514_candidate_feature_matrix_v4_summary.json")
    signal = read_optional("outputs/reports/phase5p5_repair5g514_rich_feature_signal_summary.json")
    train = read_optional("outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_train_summary.json")
    eval_summary = read_optional("outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_eval_summary.json")
    safety = read_optional("outputs/reports/phase5p5_repair5g514_static_abstention_boundary_targets_summary.json")
    g513 = read_optional("outputs/reports/phase5p5_repair5g513_decision_summary.json")

    eval_decision = eval_summary.get("decision", "")
    if eval_decision == "rich_trace_v4_ranker_passed_continue_safety_boundary_expansion":
        decision = eval_decision
        downgrade_resolved = True
    elif eval_decision == "candidate_ranker_still_simple_prior_continue_feature_design":
        decision = eval_decision
        downgrade_resolved = False
    elif eval_decision:
        decision = "rich_trace_features_insufficient_continue_probe_or_lattice"
        downgrade_resolved = False
    else:
        decision = "local_rich_feature_probe_failed_continue_export_debug"
        downgrade_resolved = False

    primary = eval_summary.get("primary_policy", {})
    gates = eval_summary.get("gates", {})
    rich_source = "existing_checkpoint" if rich.get("rich_contexts", 0) else "local_probe_required"
    summary = {
        "schema_version": "phase5p5_repair5g514_decision_summary_v1",
        "decision": decision,
        "g513_prior_decision": g513.get("decision", ""),
        "rich_feature_source": rich_source,
        "existing_checkpoint_artifact_decision": checkpoint.get("decision", ""),
        "rich_contexts": rich.get("rich_contexts", 0),
        "missing_rich_contexts": rich.get("missing_rich_contexts", 0),
        "v4_candidate_rows": v4_matrix.get("candidate_rows", 0),
        "v4_contexts": v4_matrix.get("contexts", 0),
        "v4_rich_feature_count": v4_matrix.get("rich_feature_count", 0),
        "v4_eval_decision": eval_decision,
        "v4_primary_policy": primary,
        "v4_gates": gates,
        "v4_beat_hard_controls": bool(
            gates.get("risk_adjusted_beats_safe_slow_decay_train_gate")
            and gates.get("risk_adjusted_beats_safe_train_only_map_agent_gate")
        ),
        "g513_simple_prior_downgrade_resolved": downgrade_resolved,
        "safety_preflight_decision": safety.get("decision", ""),
        "safety_package_complete": safety.get("safety_package_complete", False),
        "artifact_verification_decision": artifact.get("decision", ""),
        "rich_signal_decision": signal.get("decision", ""),
        "train_decision": train.get("decision", ""),
        **G514_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)

    policy_lines = []
    for row in eval_summary.get("policy_summaries", []):
        if row.get("policy") in {
            "v4_ranker",
            "v3_g512_ranker_reproduced",
            "safe_slow_decay_train_gate",
            "safe_train_only_map_agent_gate",
            "no_rich_feature_ablation",
            "rich_only_ranker",
            "oracle_upper_bound",
        }:
            policy_lines.append(
                f"- `{row.get('policy')}`: mean_delta_vs_static={finite_number(row.get('mean_delta_vs_static')):.6f}, "
                f"harmful={finite_number(row.get('harmful_vs_static_rate')):.3f}, "
                f"coverage={finite_number(row.get('coverage')):.3f}, "
                f"rau_0.10={finite_number(row.get('risk_adjusted_utility_lambda_0p1')):.6f}"
            )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- rich_feature_source: `{rich_source}`\n"
        f"- existing_checkpoint_artifact_decision: `{checkpoint.get('decision', '')}`\n"
        f"- rich_contexts: `{rich.get('rich_contexts', 0)}` / `{rich.get('target_contexts', 0)}`\n"
        f"- v4_candidate_rows: `{v4_matrix.get('candidate_rows', 0)}`\n"
        f"- v4_rich_feature_count: `{v4_matrix.get('rich_feature_count', 0)}`\n"
        f"- v4_beat_hard_controls: `{summary['v4_beat_hard_controls']}`\n"
        f"- g513_simple_prior_downgrade_resolved: `{downgrade_resolved}`\n"
        f"- safety_package_complete: `{summary['safety_package_complete']}`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- runtime_claim_allowed: `false`\n"
        "- learned_runtime_policy_validated: `false`\n"
        "- aaai_ready: `false`\n\n"
        "## Policy Snapshot\n\n"
        f"{chr(10).join(policy_lines) or '- no policy summaries available'}\n\n"
        "## Interpretation\n\n"
        "G5.14 recovered rich pre-choice trace features from existing checkpoint JSONL artifacts and joined them into a v4 candidate matrix without rerunning solver work. "
        "The grouped hard-control evaluation decides whether those rich features resolve the G5.13 simple-prior downgrade. "
        "Regardless of the offline result, runtime, Phase5.5, Phase6, and AAAI claims remain closed because the static/abstention/no-solution/budget/OOD safety package is still incomplete.\n",
    )
    print(json.dumps({"decision": decision, "rich_feature_source": rich_source, "v4_beat_hard_controls": summary["v4_beat_hard_controls"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
