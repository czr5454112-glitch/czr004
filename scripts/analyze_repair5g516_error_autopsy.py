"""Autopsy G5.16 false positives and missed opportunities."""

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
from repair5g516_common import (  # noqa: E402
    DEFAULT_G515_FALSE_POSITIVE_SUMMARY,
    DEFAULT_G515_SAFETY_SUMMARY,
    DEFAULT_G516_EVAL_CONTEXTS,
    DEFAULT_G516_EVAL_SUMMARY,
    DEFAULT_G516_V6_MATRIX,
    G516_CLOSED_CLAIMS,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_error_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g516_error_autopsy_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_G516_V6_MATRIX))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_G516_EVAL_CONTEXTS))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(DEFAULT_G516_EVAL_SUMMARY))
    parser.add_argument("--g515-false-positive-summary", type=Path, default=Path(DEFAULT_G515_FALSE_POSITIVE_SUMMARY))
    parser.add_argument("--g515-safety-summary", type=Path, default=Path(DEFAULT_G515_SAFETY_SUMMARY))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def full_key_for_prefix(groups: dict[str, list[dict[str, Any]]], prefix: str) -> str:
    for key in sorted(groups):
        if key.startswith(prefix):
            return key
    return prefix


def g516_primary_contexts(context_rows: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    return [row for row in context_rows if row.get("eval_scope") == "oof" and row.get("policy") == policy]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    contexts = read_csv_rows(resolve(args.context_decisions_csv, root))
    eval_summary = read_json(resolve(args.eval_summary_json, root))
    g515_fp_summary = read_json(resolve(args.g515_false_positive_summary, root))
    g515_safety = read_json(resolve(args.g515_safety_summary, root))
    groups = grouped_contexts(rows)
    primary_policy = str(eval_summary.get("primary_policy_name", ""))
    primary_rows = g516_primary_contexts(contexts, primary_policy)
    g514_false_positive_contexts = [
        full_key_for_prefix(groups, str(row.get("context_prefix", "")))
        for row in g515_fp_summary.get("autopsy_rows", [])
        if row.get("actual_harmful_vs_static") is True
    ]
    g515_false_positive_contexts = [str(key) for key in g515_safety.get("harmful_false_positive_context_keys", [])]
    g516_false_positive_contexts = []
    g516_missed_helpful = []
    for decision in primary_rows:
        key = str(decision.get("normalized_context_key", ""))
        group = groups.get(key, [])
        if not group:
            continue
        selected = select_candidate(group, str(decision.get("selected_candidate_id", "")))
        selected_delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
        if str(selected.get("candidate_id", "")) != "repair5g59_static_flow_shield" and selected_delta >= DEFAULT_MARGIN:
            g516_false_positive_contexts.append(key)
        oracle_id = str(selected.get("oracle_candidate_for_context", ""))
        oracle = select_candidate(group, oracle_id)
        oracle_delta = finite_number(oracle.get("mean_delta_vs_static_primary"), math.inf)
        if str(selected.get("candidate_id", "")) == "repair5g59_static_flow_shield" and oracle_id != "repair5g59_static_flow_shield" and oracle_delta <= -DEFAULT_MARGIN:
            static = select_candidate(group, "repair5g59_static_flow_shield")
            g516_missed_helpful.append((finite_number(static.get("oracle_regret_primary"), math.inf), key, oracle_id, oracle_delta))
    fixed_by_g516 = sorted(set(g515_false_positive_contexts) - set(g516_false_positive_contexts))
    newly_harmed = sorted(set(g516_false_positive_contexts) - set(g515_false_positive_contexts))
    top_missed = [
        {
            "normalized_context_key": key,
            "static_oracle_regret_primary": regret,
            "oracle_candidate_for_context": oracle_id,
            "oracle_delta_vs_static": oracle_delta,
        }
        for regret, key, oracle_id, oracle_delta in sorted(g516_missed_helpful, reverse=True)[:10]
    ]
    primary = eval_summary.get("primary_policy", {})
    coverage = finite_number(primary.get("coverage"), 0.0)
    hides_opportunity = coverage <= 0.05 and len(g516_missed_helpful) >= int(g515_safety.get("missed_helpful_contexts", 0))
    decision = "error_autopsy_too_conservative_continue_lattice_or_data" if hides_opportunity else "error_autopsy_completed_continue_safety_package"
    summary = {
        "schema_version": "phase5p5_repair5g516_error_autopsy_summary_v1",
        "decision": decision,
        "primary_policy_name": primary_policy,
        "g514_false_positive_contexts": g514_false_positive_contexts,
        "g515_false_positive_contexts": g515_false_positive_contexts,
        "g516_false_positive_contexts": g516_false_positive_contexts,
        "g514_false_positive_count": len(g514_false_positive_contexts),
        "g515_false_positive_count": len(g515_false_positive_contexts),
        "g516_false_positive_count": len(g516_false_positive_contexts),
        "contexts_fixed_by_g516": fixed_by_g516,
        "contexts_newly_harmed_by_g516": newly_harmed,
        "g516_missed_helpful_count": len(g516_missed_helpful),
        "top_missed_helpful_contexts": top_missed,
        "falls_back_everywhere_or_hides_opportunity": hides_opportunity,
        **G516_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Error Autopsy\n\n"
        f"- decision: `{decision}`\n"
        f"- primary_policy_name: `{primary_policy}`\n"
        f"- g514_false_positive_count: `{len(g514_false_positive_contexts)}`\n"
        f"- g515_false_positive_count: `{len(g515_false_positive_contexts)}`\n"
        f"- g516_false_positive_count: `{len(g516_false_positive_contexts)}`\n"
        f"- contexts_fixed_by_g516: `{fixed_by_g516}`\n"
        f"- contexts_newly_harmed_by_g516: `{newly_harmed}`\n"
        f"- g516_missed_helpful_count: `{len(g516_missed_helpful)}`\n"
        f"- falls_back_everywhere_or_hides_opportunity: `{hides_opportunity}`\n\n"
        "G5.16 must not pass by hiding all opportunity behind static fallback. This report keeps that failure mode explicit.\n",
    )
    print(json.dumps({"decision": decision, "g516_false_positive_count": len(g516_false_positive_contexts), "g516_missed_helpful_count": len(g516_missed_helpful)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
