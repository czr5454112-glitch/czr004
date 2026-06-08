"""Classify the G5.21 oracle-to-policy gap."""

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

from repair5g521_common import (  # noqa: E402
    G521_CANDIDATE_FEATURES_CSV,
    G521_CLOSED_CLAIMS,
    G521_CONTEXT_FEATURES_CSV,
    G521_GAP_GROUPS_CSV,
    G521_GAP_HARMFUL_CSV,
    G521_GAP_MISSED_CSV,
    G521_GAP_PARAMS_CSV,
    G521_GAP_REPORT,
    G521_GAP_SUMMARY,
    G521_SELECTOR_CALIBRATION_CSV,
    G521_SELECTOR_CONTEXT_DECISIONS_CSV,
    G521_SELECTOR_SUMMARY,
    boolish,
    csv_number,
    finite_number,
    map_agent_key,
    map_family_key,
    mean,
    numeric_candidate_param_dict,
    read_json_file,
    read_rows,
    rows_by_context,
    write_json_file,
    write_rows,
    write_text_file,
)


PARAM_FIELDS = [
    "alpha_cong_committed",
    "alpha_cong_blocked",
    "alpha_flow_progress",
    "alpha_flow_wait_or_nonprogress",
    "rho_cong",
    "rho_flow",
    "flow_shield_beta",
    "max_flow_shield",
    "c_only",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-features-csv", type=Path, default=Path(G521_CONTEXT_FEATURES_CSV))
    parser.add_argument("--candidate-features-csv", type=Path, default=Path(G521_CANDIDATE_FEATURES_CSV))
    parser.add_argument("--selector-summary-json", type=Path, default=Path(G521_SELECTOR_SUMMARY))
    parser.add_argument("--selector-decisions-csv", type=Path, default=Path(G521_SELECTOR_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--calibration-csv", type=Path, default=Path(G521_SELECTOR_CALIBRATION_CSV))
    parser.add_argument("--missed-csv", type=Path, default=Path(G521_GAP_MISSED_CSV))
    parser.add_argument("--harmful-csv", type=Path, default=Path(G521_GAP_HARMFUL_CSV))
    parser.add_argument("--groups-csv", type=Path, default=Path(G521_GAP_GROUPS_CSV))
    parser.add_argument("--params-csv", type=Path, default=Path(G521_GAP_PARAMS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G521_GAP_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_GAP_SUMMARY))
    return parser.parse_args(argv)


def best_new_oracle(group: list[dict[str, Any]]) -> dict[str, Any]:
    new_rows = [row for row in group if str(row.get("candidate_role", "")) in {"g518_retained", "g521_second_wave"}]
    oracle = [row for row in new_rows if boolish(row.get("candidate_is_new_oracle_winner"))]
    if oracle:
        return oracle[0]
    finite = [row for row in new_rows if math.isfinite(finite_number(row.get("candidate_score_primary"), math.inf))]
    return min(finite, key=lambda row: (finite_number(row.get("candidate_score_primary"), math.inf), str(row.get("candidate_id", "")))) if finite else {}


def classify_missed(decision: dict[str, Any], context: dict[str, Any], oracle: dict[str, Any]) -> str:
    reason = str(decision.get("selection_reason", ""))
    if not oracle:
        return "no_candidate_space_gain"
    if "context_gate" in reason and str(decision.get("selected_candidate_role", "")) == "old14":
        return "context_gate_false_negative"
    if "family" in reason and str(decision.get("selected_candidate_role", "")) == "old14":
        return "family_gate_false_negative"
    if "ranker" in reason and str(decision.get("selected_candidate_role", "")) in {"old14", "g518_retained", "g521_second_wave"}:
        return "candidate_ranker_missed_best_new"
    if "guard" in reason or "abstain" in reason:
        return "safety_gate_overblocked"
    if boolish(context.get("context_budget_sensitive")):
        return "budget_instability_blocked"
    if str(decision.get("selected_candidate_id", "")) == "repair5g59_static_flow_shield":
        return "static_fallback_was_correct"
    return "candidate_ranker_missed_best_new"


def classify_harmful(decision: dict[str, Any]) -> str:
    reason = str(decision.get("selection_reason", ""))
    if "context_gate" in reason:
        return "context_gate_false_positive"
    if "family" in reason:
        return "family_gate_false_positive"
    if boolish(decision.get("candidate_induced_no_solution")):
        return "risk_head_underestimated_candidate_induced_failure"
    if boolish(decision.get("budget_sensitive_candidate_failure")):
        return "budget_instability_missed"
    if str(decision.get("selected_candidate_role", "")) in {"g518_retained", "g521_second_wave"}:
        return "new_source_bias"
    return "candidate_ranker_overestimated_delta"


def param_delta_row(context: str, selected_id: str, oracle_id: str) -> dict[str, Any]:
    selected = numeric_candidate_param_dict(selected_id)
    oracle = numeric_candidate_param_dict(oracle_id)
    row = {
        "normalized_context_key": context,
        "selected_candidate_id": selected_id,
        "oracle_candidate_id": oracle_id,
    }
    for field in PARAM_FIELDS:
        row[f"selected_{field}"] = csv_number(selected[field])
        row[f"oracle_{field}"] = csv_number(oracle[field])
        row[f"delta_{field}"] = csv_number(selected[field] - oracle[field])
    row.update(G521_CLOSED_CLAIMS)
    return row


def group_rows(rows: list[dict[str, Any]], group_type: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if group_type == "map_agent_group":
            key = map_agent_key(row)
        elif group_type == "map_family":
            key = map_family_key(row)
        elif group_type == "candidate_block":
            key = str(row.get("oracle_candidate_family", row.get("selected_candidate_family", "")))
        else:
            key = str(row.get(group_type, ""))
        grouped[key].append(row)
    out = []
    for key, group in sorted(grouped.items()):
        out.append(
            {
                "group_type": group_type,
                "group_key": key,
                "rows": len(group),
                "classification_counts": dict(sorted(Counter(str(row.get("failure_classification", "")) for row in group).items())),
                **G521_CLOSED_CLAIMS,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    selector = read_json_file(args.selector_summary_json)
    best_policy = str(selector.get("best_policy", ""))
    context_rows = {str(row.get("normalized_context_key", "")): row for row in read_rows(args.context_features_csv)}
    candidate_groups = rows_by_context(read_rows(args.candidate_features_csv))
    decisions = [
        row
        for row in read_rows(args.selector_decisions_csv)
        if row.get("eval_scope") == "seed_oof" and row.get("policy") == best_policy
    ]
    decision_by_context = {str(row.get("normalized_context_key", "")): row for row in decisions}
    missed_rows = []
    harmful_rows = []
    param_rows = []
    for context, ctx in sorted(context_rows.items()):
        decision = decision_by_context.get(context, {})
        group = candidate_groups.get(context, [])
        oracle = best_new_oracle(group)
        selected_id = str(decision.get("selected_candidate_id", ""))
        selected_role = str(decision.get("selected_candidate_role", ""))
        selected_new = selected_role in {"g518_retained", "g521_second_wave"}
        opportunity = boolish(ctx.get("context_has_new_beats_old14_opportunity"))
        selected_safe_new = selected_new and boolish(decision.get("candidate_safe_policy_positive"))
        if opportunity and not selected_safe_new:
            classification = classify_missed(decision, ctx, oracle)
            missed_rows.append(
                {
                    "normalized_context_key": context,
                    "map": ctx.get("map", ""),
                    "agents": ctx.get("agents", ""),
                    "seed": ctx.get("seed", ""),
                    "policy": best_policy,
                    "selected_candidate_id": selected_id,
                    "selected_candidate_role": selected_role,
                    "selected_candidate_family": decision.get("selected_candidate_family", ""),
                    "oracle_candidate_id": oracle.get("candidate_id", ""),
                    "oracle_candidate_role": oracle.get("candidate_role", ""),
                    "oracle_candidate_family": oracle.get("candidate_family", ""),
                    "failure_classification": classification,
                    "predicted_context_opportunity": decision.get("predicted_context_opportunity", ""),
                    "predicted_avoidable_risk": decision.get("predicted_avoidable_risk", ""),
                    "selection_reason": decision.get("selection_reason", ""),
                    **G521_CLOSED_CLAIMS,
                }
            )
            if oracle:
                param_rows.append(param_delta_row(context, selected_id, str(oracle.get("candidate_id", ""))))
        harmful = selected_new and (
            boolish(decision.get("candidate_induced_no_solution"))
            or boolish(decision.get("solution_quality_harm_on_finite_pairs"))
            or boolish(decision.get("budget_sensitive_candidate_failure"))
        )
        if harmful:
            classification = classify_harmful(decision)
            harmful_rows.append(
                {
                    "normalized_context_key": context,
                    "map": ctx.get("map", ""),
                    "agents": ctx.get("agents", ""),
                    "seed": ctx.get("seed", ""),
                    "policy": best_policy,
                    "selected_candidate_id": selected_id,
                    "selected_candidate_role": selected_role,
                    "selected_candidate_family": decision.get("selected_candidate_family", ""),
                    "failure_classification": classification,
                    "predicted_avoidable_risk": decision.get("predicted_avoidable_risk", ""),
                    "selection_reason": decision.get("selection_reason", ""),
                    **G521_CLOSED_CLAIMS,
                }
            )
    group_summary = []
    for group_type in ["map_agent_group", "map_family", "candidate_block", "selected_candidate_family", "oracle_candidate_family"]:
        group_summary.extend(group_rows(missed_rows + harmful_rows, group_type))
    calibration = read_rows(args.calibration_csv)
    best_calibration = [row for row in calibration if row.get("policy") == best_policy and row.get("row_type") == "avoidable_risk_calibration_bucket"]
    ece = mean([finite_number(row.get("ece_abs_error"), math.nan) for row in best_calibration if str(row.get("ece_abs_error", "")) != ""])
    decision = "oracle_to_policy_gap_autopsy_completed"
    summary = {
        "schema_version": "phase5p5_repair5g521_oracle_to_policy_gap_summary_v1",
        "decision": decision,
        "best_policy": best_policy,
        "missed_opportunity_contexts": len(missed_rows),
        "harmful_new_false_positive_contexts": len(harmful_rows),
        "missed_classification_counts": dict(sorted(Counter(row["failure_classification"] for row in missed_rows).items())),
        "harmful_classification_counts": dict(sorted(Counter(row["failure_classification"] for row in harmful_rows).items())),
        "parameter_delta_rows": len(param_rows),
        "group_summary_rows": len(group_summary),
        "calibration_ece_avoidable_risk": ece,
        **G521_CLOSED_CLAIMS,
    }
    write_rows(args.missed_csv, missed_rows)
    write_rows(args.harmful_csv, harmful_rows)
    write_rows(args.groups_csv, group_summary)
    write_rows(args.params_csv, param_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.21 Oracle-to-Policy Gap Autopsy\n\n"
        f"- decision: `{decision}`\n"
        f"- best_policy: `{best_policy}`\n"
        f"- missed_opportunity_contexts: `{len(missed_rows)}`\n"
        f"- harmful_new_false_positive_contexts: `{len(harmful_rows)}`\n"
        f"- missed_classification_counts: `{summary['missed_classification_counts']}`\n"
        f"- harmful_classification_counts: `{summary['harmful_classification_counts']}`\n"
        f"- calibration_ece_avoidable_risk: `{csv_number(ece)}`\n",
    )
    print(json.dumps({"decision": decision, "best_policy": best_policy, "missed": len(missed_rows), "harmful": len(harmful_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
