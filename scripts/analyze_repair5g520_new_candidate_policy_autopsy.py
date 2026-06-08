"""Autopsy G5.20 new-candidate policy selections and missed opportunities."""

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

from repair5g520_common import (  # noqa: E402
    G520_AUTOPSY_CSV,
    G520_AUTOPSY_REPORT,
    G520_AUTOPSY_SUMMARY,
    G520_CLOSED_CLAIMS,
    G520_POLICY_CONTEXT_DECISIONS_CSV,
    G520_POLICY_SUMMARY,
    G520_TARGETS_CSV,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    csv_number,
    finite_number,
    map_agent_key,
    map_family_key,
    read_json_file,
    read_rows,
    row_key,
    rows_by_context,
    select_candidate,
    total_harmful,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G520_TARGETS_CSV))
    parser.add_argument("--policy-summary-json", type=Path, default=Path(G520_POLICY_SUMMARY))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(G520_POLICY_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G520_AUTOPSY_CSV))
    parser.add_argument("--report", type=Path, default=Path(G520_AUTOPSY_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G520_AUTOPSY_SUMMARY))
    return parser.parse_args(argv)


def target_key(context: str, candidate: str) -> str:
    return f"{context}|{candidate}"


def selected_target(decision: dict[str, Any], targets_by_key: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return targets_by_key.get(target_key(str(decision.get("normalized_context_key", "")), str(decision.get("selected_candidate_id", ""))), {})


def old14_oracle_target(group: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [row for row in group if boolish(row.get("is_old14_candidate")) and math.isfinite(finite_number(row.get("score_primary"), math.inf))]
    return min(candidates, key=lambda row: (finite_number(row.get("score_primary"), math.inf), str(row.get("candidate_id", "")))) if candidates else {}


def autopsy_base_row(
    row_type: str,
    context: str,
    group: list[dict[str, Any]],
    decision: dict[str, Any] | None,
    targets_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    first = group[0]
    static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
    old14 = old14_oracle_target(group)
    oracle_new_id = str(first.get("oracle_new_candidate_for_context", ""))
    oracle_new = targets_by_key.get(target_key(context, oracle_new_id), {})
    selected = selected_target(decision or {}, targets_by_key) if decision else {}
    return {
        "row_type": row_type,
        "normalized_context_key": context,
        "map": first.get("map", ""),
        "agents": first.get("agents", ""),
        "seed": first.get("seed", ""),
        "map_agent_group": map_agent_key(first),
        "map_family": map_family_key(first),
        "selected_policy_candidate": (decision or {}).get("selected_candidate_id", ""),
        "selected_candidate_source": selected.get("candidate_source", ""),
        "selected_candidate_family": selected.get("candidate_family", ""),
        "selected_total_harmful": (decision or {}).get("total_harmful", selected.get("harmful_total", "")),
        "selected_solution_quality_delta_vs_static": (decision or {}).get("solution_quality_delta_vs_static", selected.get("solution_quality_delta_vs_static", "")),
        "oracle_new_candidate": oracle_new_id,
        "oracle_new_candidate_delta_vs_static": oracle_new.get("solution_quality_delta_vs_static", ""),
        "old14_oracle_candidate": old14.get("candidate_id", ""),
        "old14_oracle_delta_vs_static": old14.get("solution_quality_delta_vs_static", ""),
        "static_candidate": static.get("candidate_id", ""),
        "static_total_harmful": static.get("harmful_total", ""),
        "new_candidate_best_gap_vs_old14": first.get("new_candidate_best_gap_vs_old14", ""),
        "predicted_new_opportunity_probability": (decision or {}).get("predicted_new_opportunity_prob", ""),
        "predicted_harmful_risk": (decision or {}).get("predicted_harmful_risk", ""),
        "selection_reason": (decision or {}).get("selection_reason", ""),
        "new_opportunity_context": first.get("new_opportunity_context", ""),
        "new_candidate_win_context": first.get("new_candidate_win_context", ""),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = read_rows(args.targets_csv)
    targets_by_key = {row_key(row): row for row in targets}
    policy_summary = read_json_file(args.policy_summary_json)
    best_policy = str(policy_summary.get("best_policy", ""))
    context_decisions = [
        row
        for row in read_rows(args.context_decisions_csv)
        if row.get("eval_scope") == "seed_oof" and row.get("policy") == best_policy
    ]
    decisions_by_context = {str(row.get("normalized_context_key", "")): row for row in context_decisions}
    groups = rows_by_context(targets)
    out_rows: list[dict[str, Any]] = []

    new_win_contexts = [
        (context, group)
        for context, group in groups.items()
        if boolish(group[0].get("new_candidate_win_context"))
    ]
    new_win_contexts.sort(key=lambda item: finite_number(item[1][0].get("new_candidate_best_gap_vs_old14"), math.inf))
    for context, group in new_win_contexts[:16]:
        out_rows.append(autopsy_base_row("top_16_g518_new_candidate_win_context", context, group, decisions_by_context.get(context), targets_by_key))

    missed_new = []
    false_positive_new = []
    picked_old_when_new_best = []
    selected_new_old_static_safer = []
    capture_by_map_agent: dict[str, list[bool]] = defaultdict(list)
    capture_by_family: dict[str, list[bool]] = defaultdict(list)
    for context, group in sorted(groups.items()):
        decision = decisions_by_context.get(context)
        if not decision:
            continue
        selected = selected_target(decision, targets_by_key)
        opp = boolish(group[0].get("new_opportunity_context"))
        selected_new = boolish(selected.get("is_new_candidate"))
        if opp:
            capture_by_map_agent[map_agent_key(group[0])].append(selected_new)
            capture_by_family[map_family_key(group[0])].append(selected_new)
        if selected_new and total_harmful(selected):
            false_positive_new.append((context, group, decision))
            out_rows.append(autopsy_base_row("false_positive_involving_new_candidate", context, group, decision, targets_by_key))
        if opp and not selected_new:
            missed_new.append((context, group, decision))
            out_rows.append(autopsy_base_row("missed_new_opportunity", context, group, decision, targets_by_key))
            if str(decision.get("selected_candidate_id", "")) in {STATIC_FLOW_SHIELD_CANDIDATE, str(old14_oracle_target(group).get("candidate_id", ""))}:
                picked_old_when_new_best.append((context, group, decision))
        if selected_new:
            static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
            old14 = old14_oracle_target(group)
            selected_rau = finite_number(selected.get("solution_quality_delta_vs_static"), 0.0) + (0.10 if total_harmful(selected) else 0.0)
            safer_old_static = False
            for control in [static, old14]:
                if control and not total_harmful(control):
                    control_rau = finite_number(control.get("solution_quality_delta_vs_static"), 0.0)
                    safer_old_static = safer_old_static or control_rau <= selected_rau
            if safer_old_static:
                selected_new_old_static_safer.append((context, group, decision))
                out_rows.append(autopsy_base_row("new_selected_but_old_or_static_safer", context, group, decision, targets_by_key))

    for key, captures in sorted(capture_by_map_agent.items()):
        out_rows.append(
            {
                "row_type": "per_map_agent_opportunity_capture",
                "group_key": key,
                "opportunity_contexts": len(captures),
                "captured_contexts": sum(1 for value in captures if value),
                "capture_rate": sum(1 for value in captures if value) / len(captures) if captures else 0.0,
            }
        )
    for key, captures in sorted(capture_by_family.items()):
        out_rows.append(
            {
                "row_type": "per_family_opportunity_capture",
                "group_key": key,
                "opportunity_contexts": len(captures),
                "captured_contexts": sum(1 for value in captures if value),
                "capture_rate": sum(1 for value in captures if value) / len(captures) if captures else 0.0,
            }
        )

    new_winner_candidates = Counter(group[0].get("oracle_new_candidate_for_context", "") for _context, group in new_win_contexts)
    best = policy_summary.get("best_policy_summary", {})
    summary = {
        "schema_version": "phase5p5_repair5g520_new_candidate_policy_autopsy_summary_v1",
        "decision": "new_candidate_policy_autopsy_completed",
        "best_policy": best_policy,
        "top_16_rows_written": min(16, len(new_win_contexts)),
        "new_candidate_win_contexts": len(new_win_contexts),
        "missed_new_opportunities": len(missed_new),
        "false_positives_involving_new_candidates": len(false_positive_new),
        "contexts_where_new_best_but_policy_picks_old_or_static": len(picked_old_when_new_best),
        "contexts_where_new_selected_but_old_static_safer": len(selected_new_old_static_safer),
        "new_candidate_opportunity_capture_rate": best.get("new_candidate_opportunity_capture_rate", ""),
        "new_candidate_selection_count": best.get("new_candidate_selection_count", ""),
        "new_candidate_helpful_selection_count": best.get("new_candidate_helpful_selection_count", ""),
        "new_candidate_harmful_selection_count": best.get("new_candidate_harmful_selection_count", ""),
        "top_recurrent_new_winners": dict(new_winner_candidates.most_common(8)),
        **G520_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, out_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 New-Candidate Policy Autopsy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- best_policy: `{best_policy}`\n"
        f"- new_candidate_win_contexts: `{len(new_win_contexts)}`\n"
        f"- missed_new_opportunities: `{len(missed_new)}`\n"
        f"- false_positives_involving_new_candidates: `{len(false_positive_new)}`\n"
        f"- contexts_where_new_best_but_policy_picks_old_or_static: `{len(picked_old_when_new_best)}`\n"
        f"- contexts_where_new_selected_but_old_static_safer: `{len(selected_new_old_static_safer)}`\n"
        f"- new_candidate_opportunity_capture_rate: `{summary['new_candidate_opportunity_capture_rate']}`\n"
        f"- top_recurrent_new_winners: `{summary['top_recurrent_new_winners']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The CSV includes the top G5.18 new-candidate win contexts, false positives, missed opportunities, old/static safer cases, and per-map-agent/family capture rows.\n",
    )
    print(json.dumps({"decision": summary["decision"], "best_policy": best_policy, "missed_new_opportunities": len(missed_new)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
