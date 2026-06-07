"""Analyze G5.14 harmful false positives under the G5.15 diagnostics."""

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

from repair5g512_common import DEFAULT_MARGIN, finite_number, read_csv_rows, read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g513_common import grouped_contexts, select_candidate  # noqa: E402
from repair5g515_common import (  # noqa: E402
    DEFAULT_EVAL_CONTEXTS,
    DEFAULT_EVAL_SUMMARY,
    DEFAULT_V5_MATRIX,
    G515_CLOSED_CLAIMS,
)


DEFAULT_V4_CONTEXTS = "outputs/tables/phase5p5_repair5g514_candidate_ranker_v4_context_decisions.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_false_positive_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g515_false_positive_autopsy_summary.json"
TARGETS = [
    {
        "prefix": "maze-32-32-4|a50|s151",
        "expected_selected": "repair5g59_slow_decay_high_shield",
        "expected_oracle": "repair5g59_wait_aggressive",
    },
    {
        "prefix": "random-32-32-20|a50|s151",
        "expected_selected": "repair5g59_slow_decay_high_shield",
        "expected_oracle": "repair5g59_commit_heavy_flow_guard",
    },
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_V5_MATRIX))
    parser.add_argument("--v4-context-csv", type=Path, default=Path(DEFAULT_V4_CONTEXTS))
    parser.add_argument("--g515-context-csv", type=Path, default=Path(DEFAULT_EVAL_CONTEXTS))
    parser.add_argument("--g515-summary-json", type=Path, default=Path(DEFAULT_EVAL_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def score_primary(row: dict[str, Any]) -> float:
    values = [
        finite_number(row.get("score_1000"), math.nan),
        finite_number(row.get("score_2000"), math.nan),
    ]
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else math.inf


def find_context(rows: list[dict[str, Any]], prefix: str, *, policy: str | None = None, scope: str | None = None) -> dict[str, Any] | None:
    for row in rows:
        key = str(row.get("normalized_context_key", ""))
        if not key.startswith(prefix):
            continue
        if policy is not None and row.get("policy") != policy:
            continue
        if scope is not None and row.get("eval_scope") != scope:
            continue
        return row
    return None


def group_for_prefix(groups: dict[str, list[dict[str, Any]]], prefix: str) -> list[dict[str, Any]]:
    for key, group in groups.items():
        if key.startswith(prefix):
            return group
    return []


def compact_rich_values(row: dict[str, Any]) -> dict[str, Any]:
    wanted = [
        "feature_rich_blocked_per_committed",
        "feature_rich_blocked_per_agent",
        "feature_rich_wait_per_committed",
        "feature_rich_wait_event_count",
        "feature_rich_progress_ratio",
        "feature_rich_c_flow_update_ratio",
        "feature_rich_cost_span",
        "feature_rich_cost_max",
    ]
    return {name: row.get(name, "") for name in wanted}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    v4_contexts = read_csv_rows(resolve(args.v4_context_csv, root))
    g515_contexts = read_csv_rows(resolve(args.g515_context_csv, root)) if resolve(args.g515_context_csv, root).exists() else []
    g515_summary = read_json(resolve(args.g515_summary_json, root)) if resolve(args.g515_summary_json, root).exists() else {}
    primary_policy = str(g515_summary.get("primary_policy_name", ""))
    groups = grouped_contexts(rows)
    autopsy_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        prefix = target["prefix"]
        group = group_for_prefix(groups, prefix)
        if not group:
            autopsy_rows.append({"context_prefix": prefix, "found": False})
            continue
        v4 = find_context(v4_contexts, prefix, policy="v4_ranker") or find_context(v4_contexts, prefix)
        g515 = find_context(g515_contexts, prefix, policy=primary_policy, scope="oof") or find_context(g515_contexts, prefix, policy=primary_policy)
        selected_id = str((v4 or {}).get("selected_candidate_id", target["expected_selected"]))
        selected = select_candidate(group, selected_id)
        static = select_candidate(group, "repair5g59_static_flow_shield")
        oracle_id = str(selected.get("oracle_candidate_for_context", target["expected_oracle"]))
        oracle = select_candidate(group, oracle_id)
        selected_delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
        predicted_risk = finite_number((v4 or {}).get("predicted_best_harmful_risk"), math.nan)
        autopsy_rows.append(
            {
                "context_prefix": prefix,
                "found": True,
                "selected_candidate": selected_id,
                "expected_selected": target["expected_selected"],
                "oracle_candidate": oracle_id,
                "expected_oracle": target["expected_oracle"],
                "static_score_primary": score_primary(static),
                "selected_score_primary": score_primary(selected),
                "oracle_score_primary": score_primary(oracle),
                "actual_mean_delta_vs_static": selected_delta,
                "actual_harmful_vs_static": selected_delta >= DEFAULT_MARGIN,
                "g514_predicted_risk": predicted_risk,
                "g514_predicted_margin": (v4 or {}).get("predicted_margin", ""),
                "g515_primary_policy": primary_policy,
                "g515_selected_candidate": (g515 or {}).get("selected_candidate_id", ""),
                "g515_predicted_risk": (g515 or {}).get("predicted_best_harmful_risk", ""),
                "g515_predicted_margin": (g515 or {}).get("predicted_margin", ""),
                "rich_features": compact_rich_values(static),
                "risk_underprediction_reason": "selected candidate was actually harmful while predicted risk stayed below the gate threshold"
                if math.isfinite(predicted_risk) and predicted_risk <= 0.075 and selected_delta >= DEFAULT_MARGIN
                else "selected candidate was harmful; conservative rank or context-risk gate should abstain",
                "gate_that_should_have_abstained": "harmful_risk_upper_bound_or_context_uncertainty_gate",
            }
        )
    harmful_found = sum(1 for row in autopsy_rows if row.get("actual_harmful_vs_static") is True)
    summary = {
        "schema_version": "phase5p5_repair5g515_false_positive_autopsy_summary_v1",
        "decision": "false_positive_autopsy_completed_continue_safety_update",
        "target_contexts": len(TARGETS),
        "targets_found": sum(1 for row in autopsy_rows if row.get("found")),
        "harmful_targets_confirmed": harmful_found,
        "primary_policy_name": primary_policy,
        "autopsy_rows": autopsy_rows,
        **G515_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    lines = []
    for row in autopsy_rows:
        lines.append(
            f"### {row.get('context_prefix')}\n\n"
            f"- selected_candidate: `{row.get('selected_candidate', '')}`\n"
            f"- oracle_candidate: `{row.get('oracle_candidate', '')}`\n"
            f"- static_score_primary: `{row.get('static_score_primary', '')}`\n"
            f"- selected_score_primary: `{row.get('selected_score_primary', '')}`\n"
            f"- oracle_score_primary: `{row.get('oracle_score_primary', '')}`\n"
            f"- actual_mean_delta_vs_static: `{row.get('actual_mean_delta_vs_static', '')}`\n"
            f"- g514_predicted_risk: `{row.get('g514_predicted_risk', '')}`\n"
            f"- g514_predicted_margin: `{row.get('g514_predicted_margin', '')}`\n"
            f"- g515_primary_policy: `{row.get('g515_primary_policy', '')}`\n"
            f"- g515_selected_candidate: `{row.get('g515_selected_candidate', '')}`\n"
            f"- g515_predicted_risk: `{row.get('g515_predicted_risk', '')}`\n"
            f"- g515_predicted_margin: `{row.get('g515_predicted_margin', '')}`\n"
            f"- rich_features: `{row.get('rich_features', {})}`\n"
            f"- risk_underprediction_reason: `{row.get('risk_underprediction_reason', '')}`\n"
            f"- gate_that_should_have_abstained: `{row.get('gate_that_should_have_abstained', '')}`\n"
        )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 False-Positive Autopsy\n\n"
        "- decision: `false_positive_autopsy_completed_continue_safety_update`\n"
        f"- harmful_targets_confirmed: `{harmful_found}`\n"
        f"- primary_policy_name: `{primary_policy}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        + "\n".join(lines),
    )
    print(json.dumps({"decision": summary["decision"], "harmful_targets_confirmed": harmful_found}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
