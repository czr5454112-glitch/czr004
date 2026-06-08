"""Evaluate G5.16 pessimistic rankers with deeper split diagnostics."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from eval_repair5g515_calibrated_interaction_rankers import evaluate_once as evaluate_g515_once  # noqa: E402
from repair5g512_common import ADDITIVE_CANDIDATE, STATIC_FLOW_SHIELD_CANDIDATE, finite_number, leakage_scan, observed_id_flags, read_csv_rows, read_json, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g515_common import bootstrap_rows, calibration_rows, grouped_candidate_count_ok, harmful_group_rows, rows_by_seed, rows_with_seed, rows_without_seed, summary_by_policy  # noqa: E402
from repair5g516_common import (  # noqa: E402
    DEFAULT_G515_DECISION_SUMMARY,
    DEFAULT_G515_SAFETY_SUMMARY,
    DEFAULT_G516_EVAL_CONTEXTS,
    DEFAULT_G516_EVAL_SUMMARY,
    DEFAULT_G516_V6_MATRIX,
    G516_CLOSED_CLAIMS,
    PROMOTION_HARMFUL_LIMIT,
    VARIANT_CONFIGS,
    add_scope_to_extended_summaries,
    fit_pessimistic_model,
    g516_feature_names,
    harmful_candidate_rows,
    map_agent_key,
    policy_summary_extended,
    rename_policy_selected,
    risk_adjusted_metric,
    select_pessimistic_policy,
    simple_selected_for_candidate,
    strip_g516_error_features,
)
from repair5g515_common import context_row  # noqa: E402


DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g516_pessimistic_rankers_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_pessimistic_rankers.md"
RENAME_G515_POLICIES = {
    "two_stage_safety_ranker": "g515_two_stage_safety_ranker",
    "pairwise_context_ranker": "g515_pairwise_context_ranker",
    "rich_interactions_shuffled_within_train_split": "rich_interactions_shuffled_control",
    "true_random_feature_model": "random_feature_model",
    "true_shuffled_label_model": "shuffled_label_model",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_G516_V6_MATRIX))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_G516_EVAL_CONTEXTS))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_G516_EVAL_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--bootstrap-samples", type=int, default=500)
    return parser.parse_args(argv)


def merge_selected(target: dict[str, list[dict[str, Any]]], source: dict[str, list[dict[str, Any]]]) -> None:
    for policy, rows in source.items():
        target.setdefault(policy, []).extend(rows)


def simple_context_rows(policy: str, selected: list[dict[str, Any]], *, reason: str, eval_scope: str, fold_seed: int | str | None) -> list[dict[str, Any]]:
    return [context_row(policy, row, reason, eval_scope=eval_scope, fold_seed=fold_seed) for row in selected]


def add_required_simple_baselines(
    selected: dict[str, list[dict[str, Any]]],
    contexts: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    eval_scope: str,
    fold_seed: int | str | None,
) -> None:
    static = simple_selected_for_candidate(eval_rows, STATIC_FLOW_SHIELD_CANDIDATE)
    additive = simple_selected_for_candidate(eval_rows, ADDITIVE_CANDIDATE)
    selected["static_flow_shield"] = static
    selected["additive_ltm"] = additive
    contexts.extend(simple_context_rows("static_flow_shield", static, reason="fixed_static_flow_shield", eval_scope=eval_scope, fold_seed=fold_seed))
    contexts.extend(simple_context_rows("additive_ltm", additive, reason="fixed_additive_ltm", eval_scope=eval_scope, fold_seed=fold_seed))


def evaluate_once(
    train_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    eval_scope: str,
    fold_seed: int | str | None,
    ridge_alpha: float,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    contexts: list[dict[str, Any]] = []
    baseline_selected, baseline_contexts = evaluate_g515_once(
        strip_g516_error_features(train_rows),
        strip_g516_error_features(eval_rows),
        eval_scope=eval_scope,
        fold_seed=fold_seed,
        ridge_alpha=ridge_alpha,
    )
    renamed_selected, renamed_contexts = rename_policy_selected(baseline_selected, baseline_contexts, RENAME_G515_POLICIES)
    merge_selected(selected, renamed_selected)
    contexts.extend(renamed_contexts)
    add_required_simple_baselines(selected, contexts, eval_rows, eval_scope=eval_scope, fold_seed=fold_seed)

    features = g516_feature_names(train_rows, include_error_bank=True)
    model = fit_pessimistic_model(
        train_rows,
        feature_names=features,
        ridge_alpha=ridge_alpha,
        model_type=f"fold_{eval_scope}_pessimistic_bound",
    )
    no_error_model = fit_pessimistic_model(
        train_rows,
        feature_names=g516_feature_names(train_rows, include_error_bank=False),
        ridge_alpha=ridge_alpha,
        model_type=f"fold_{eval_scope}_no_error_bank_feature_ablation",
    )
    for policy, config in VARIANT_CONFIGS.items():
        policy_selected, policy_contexts = select_pessimistic_policy(
            eval_rows,
            model,
            policy=policy,
            config=config,
            eval_scope=eval_scope,
            fold_seed=fold_seed,
        )
        selected[policy] = policy_selected
        contexts.extend(policy_contexts)
    no_error_selected, no_error_contexts = select_pessimistic_policy(
        eval_rows,
        no_error_model,
        policy="no_error_bank_feature_ablation",
        config=VARIANT_CONFIGS["balanced_bound"],
        eval_scope=eval_scope,
        fold_seed=fold_seed,
        ignore_error_bank_gates=True,
    )
    selected["no_error_bank_feature_ablation"] = no_error_selected
    contexts.extend(no_error_contexts)
    no_bound_selected, no_bound_contexts = select_pessimistic_policy(
        eval_rows,
        model,
        policy="no_pessimistic_bound_ablation",
        config=VARIANT_CONFIGS["balanced_bound"],
        eval_scope=eval_scope,
        fold_seed=fold_seed,
        use_bounds=False,
    )
    selected["no_pessimistic_bound_ablation"] = no_bound_selected
    contexts.extend(no_bound_contexts)
    return selected, contexts


def summarize_selected_map(selected: dict[str, list[dict[str, Any]]], universe_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = [
        "ultra_safe_bound",
        "balanced_bound",
        "opportunity_diagnostic_not_for_promotion",
        "no_error_bank_feature_ablation",
        "no_pessimistic_bound_ablation",
        "static_flow_shield",
        "additive_ltm",
        "v3_g512_ranker_reproduced",
        "v4_g514_ranker_reproduced",
        "g515_pairwise_context_ranker",
        "g515_two_stage_safety_ranker",
        "safe_slow_decay_train_gate",
        "safe_train_only_map_agent_gate",
        "map_agent_only_gate",
        "fixed_slow_decay_high_shield",
        "candidate_param_only_ranker",
        "rich_interactions_shuffled_control",
        "random_feature_model",
        "shuffled_label_model",
        "oracle_upper_bound",
    ]
    return [policy_summary_extended(policy, selected[policy], universe_rows) for policy in order if policy in selected]


def lomo_groups(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({map_agent_key(row) for row in rows})


def better(lhs: dict[str, Any], rhs: dict[str, Any], suffix: str) -> bool:
    return risk_adjusted_metric(lhs, suffix) < risk_adjusted_metric(rhs, suffix)


def choose_primary(oof_by_policy: dict[str, dict[str, Any]]) -> str:
    candidates = [policy for policy in ["ultra_safe_bound", "balanced_bound"] if policy in oof_by_policy]
    if not candidates:
        return ""
    return min(
        candidates,
        key=lambda policy: (
            risk_adjusted_metric(oof_by_policy[policy], "0p10"),
            -finite_number(oof_by_policy[policy].get("coverage"), 0.0),
            policy,
        ),
    )


def decision_from_gates(gates: dict[str, bool], primary: dict[str, Any], diagnostic: dict[str, Any], g515_primary: dict[str, Any]) -> str:
    required = [
        "harmful_vs_static_rate_le_0p033",
        "rau_0p05_beats_g515_primary",
        "rau_0p10_beats_g515_primary",
        "rau_0p10_beats_reproduced_v4",
        "beats_safe_slow_decay_train_gate",
        "beats_safe_train_only_map_agent_gate",
        "beats_rich_interactions_shuffled_control",
        "false_positive_count_le_g515",
        "missed_helpful_count_reduced_vs_g515",
        "forbidden_feature_count_eq_0",
        "no_ids_166_205",
        "runtime_claim_allowed_false",
    ]
    if all(gates.get(key, False) for key in required):
        return "pessimistic_ranker_passed_continue_targeted_local_probe"
    if (
        diagnostic
        and better(diagnostic, g515_primary, "0p10")
        and finite_number(diagnostic.get("harmful_vs_static_rate"), math.inf) > PROMOTION_HARMFUL_LIMIT
    ):
        return "opportunity_improved_but_safety_failed_continue_calibration"
    if finite_number(primary.get("coverage"), 0.0) <= 0.05 or not gates.get("missed_helpful_count_reduced_vs_g515", False):
        return "pessimistic_ranker_too_conservative_continue_lattice_or_data"
    return "pessimistic_ranker_no_better_than_g515_continue_feature_design"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    leak = leakage_scan(g516_feature_names(rows, include_error_bank=True))
    flags = observed_id_flags(rows)
    g515_decision = read_json(resolve(DEFAULT_G515_DECISION_SUMMARY, root))
    g515_safety = read_json(resolve(DEFAULT_G515_SAFETY_SUMMARY, root))
    g515_primary = g515_decision.get("primary_policy", {})
    g515_false_positive_count = int(g515_safety.get("harmful_false_positive_contexts", 999999))
    g515_missed_helpful_count = int(g515_safety.get("missed_helpful_contexts", 999999))

    oof_selected: dict[str, list[dict[str, Any]]] = {}
    context_rows: list[dict[str, Any]] = []
    for seed in rows_by_seed(rows):
        fold_selected, fold_contexts = evaluate_once(
            rows_without_seed(rows, seed),
            rows_with_seed(rows, seed),
            eval_scope="oof",
            fold_seed=seed,
            ridge_alpha=args.ridge_alpha,
        )
        merge_selected(oof_selected, fold_selected)
        context_rows.extend(fold_contexts)

    lomo_selected: dict[str, list[dict[str, Any]]] = {}
    for group_key in lomo_groups(rows):
        train_rows = [row for row in rows if map_agent_key(row) != group_key]
        eval_rows = [row for row in rows if map_agent_key(row) == group_key]
        fold_selected, fold_contexts = evaluate_once(
            train_rows,
            eval_rows,
            eval_scope="leave_one_map_agent_group_out",
            fold_seed=group_key,
            ridge_alpha=args.ridge_alpha,
        )
        merge_selected(lomo_selected, fold_selected)
        context_rows.extend(fold_contexts)

    dev_train = [row for row in rows if row.get("split") == "train"]
    dev_eval = [row for row in rows if row.get("split") == "dev"]
    dev_selected, dev_contexts = evaluate_once(
        dev_train,
        dev_eval,
        eval_scope="fixed_146_150_train_151_155_dev",
        fold_seed="151_155",
        ridge_alpha=args.ridge_alpha,
    )
    context_rows.extend(dev_contexts)

    oof_summaries = summarize_selected_map(oof_selected, rows)
    lomo_summaries = summarize_selected_map(lomo_selected, rows)
    dev_summaries = summarize_selected_map(dev_selected, dev_eval)
    oof_by_policy = summary_by_policy(oof_summaries)
    primary_policy_name = choose_primary(oof_by_policy)
    primary = oof_by_policy.get(primary_policy_name, {})
    diagnostic = oof_by_policy.get("opportunity_diagnostic_not_for_promotion", {})

    gates = {
        "harmful_vs_static_rate_le_0p033": finite_number(primary.get("harmful_vs_static_rate"), math.inf) <= PROMOTION_HARMFUL_LIMIT,
        "rau_0p05_beats_g515_primary": better(primary, g515_primary, "0p05"),
        "rau_0p10_beats_g515_primary": better(primary, g515_primary, "0p10"),
        "rau_0p10_beats_reproduced_v4": better(primary, oof_by_policy.get("v4_g514_ranker_reproduced", {}), "0p10"),
        "beats_safe_slow_decay_train_gate": better(primary, oof_by_policy.get("safe_slow_decay_train_gate", {}), "0p10"),
        "beats_safe_train_only_map_agent_gate": better(primary, oof_by_policy.get("safe_train_only_map_agent_gate", {}), "0p10"),
        "beats_rich_interactions_shuffled_control": better(primary, oof_by_policy.get("rich_interactions_shuffled_control", {}), "0p10"),
        "false_positive_count_le_g515": finite_number(primary.get("false_positive_count"), math.inf) <= g515_false_positive_count,
        "missed_helpful_count_reduced_vs_g515": finite_number(primary.get("missed_helpful_count"), math.inf) < g515_missed_helpful_count,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "no_ids_166_205": flags["ids_166_205_untouched"],
        "runtime_claim_allowed_false": G516_CLOSED_CLAIMS["runtime_claim_allowed"] is False,
    }
    decision = decision_from_gates(gates, primary, diagnostic, g515_primary)
    eval_rows_out = (
        add_scope_to_extended_summaries("oof", oof_summaries)
        + add_scope_to_extended_summaries("leave_one_map_agent_group_out", lomo_summaries)
        + add_scope_to_extended_summaries("fixed_146_150_train_151_155_dev", dev_summaries)
        + bootstrap_rows(oof_selected, samples=args.bootstrap_samples)
        + calibration_rows(context_rows, policies=["ultra_safe_bound", "balanced_bound", "opportunity_diagnostic_not_for_promotion"])
        + harmful_group_rows(oof_selected)
        + harmful_candidate_rows(oof_selected)
        + [
            {
                "row_type": "targeted_bank_split_note",
                "policy": "not_applicable_no_targeted_probe",
                "eval_scope": "original_bank_vs_targeted_bank",
                "contexts": 0,
            }
        ]
    )
    write_csv_rows(resolve(args.output_csv, root), eval_rows_out)
    write_csv_rows(resolve(args.context_decisions_csv, root), context_rows)
    summary = {
        "schema_version": "phase5p5_repair5g516_pessimistic_rankers_summary_v1",
        "decision": decision,
        "primary_policy_name": primary_policy_name,
        "primary_policy": primary,
        "opportunity_diagnostic_policy": diagnostic,
        "oof_contexts": len({str(row.get("normalized_context_key", "")) for row in rows}),
        "oof_policy_summaries": oof_summaries,
        "leave_one_map_agent_group_out_policy_summaries": lomo_summaries,
        "fixed_dev_policy_summaries": dev_summaries,
        "bootstrap_confidence_intervals_reported": True,
        "calibration_buckets_reported": True,
        "per_map_agent_harmful_counts_reported": True,
        "per_seed_harmful_counts_reported": True,
        "per_candidate_harmful_counts_reported": True,
        "targeted_bank_split_reported": False,
        "targeted_bank_split_reason": "targeted probe skipped; no augmented targeted-bank outcomes exist",
        "grouped_oof_sanity": {
            "exactly_14_candidate_rows_per_context": grouped_candidate_count_ok(rows),
            "seed_oof_folds": rows_by_seed(rows),
            "leave_one_map_agent_groups": lomo_groups(rows),
        },
        "g515_primary_policy_for_comparison": g515_primary,
        "g515_false_positive_count": g515_false_positive_count,
        "g515_missed_helpful_count": g515_missed_helpful_count,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **flags,
        **G516_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    policy_lines = "\n".join(
        f"- `{row['policy']}`: mean_delta_vs_static={finite_number(row.get('mean_delta_vs_static'), math.inf):.6f}, "
        f"harmful_rate={finite_number(row.get('harmful_vs_static_rate'), math.inf):.3f}, "
        f"coverage={finite_number(row.get('coverage'), math.inf):.3f}, "
        f"rau_0.10={risk_adjusted_metric(row, '0p10'):.6f}, "
        f"fp={row.get('false_positive_count')}, missed={row.get('missed_helpful_count')}"
        for row in oof_summaries
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Pessimistic Ranker Evaluation\n\n"
        f"- decision: `{decision}`\n"
        f"- primary_policy_name: `{primary_policy_name}`\n"
        f"- primary_policy: `{primary}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n"
        "- seed_oof_146_155: `reported`\n"
        "- leave_one_map_agent_group_out: `reported`\n"
        "- fixed_train_146_150_dev_151_155: `reported`\n"
        "- original_bank_vs_targeted_bank: `not_applicable_no_targeted_probe`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## OOF Policy Summaries\n\n"
        f"{policy_lines}\n",
    )
    print(json.dumps({"decision": decision, "primary_policy_name": primary_policy_name, "primary_harmful": primary.get("harmful_vs_static_rate", "")}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
