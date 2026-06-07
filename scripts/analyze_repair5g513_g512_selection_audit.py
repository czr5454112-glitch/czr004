"""Audit G5.12 grouped selections for Repair5G.5.13."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    DEFAULT_MARGIN,
    SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    count_by,
    finite_number,
    map_family,
    mean,
    observed_id_flags,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g513_common import G513_CLOSED_CLAIMS, grouped_contexts, oracle_candidate, select_candidate  # noqa: E402


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_DECISIONS = "outputs/tables/phase5p5_repair5g512_candidate_ranker_context_decisions.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g513_g512_selection_audit.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g513_g512_selection_audit.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g513_g512_selection_audit_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_DECISIONS))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def helpful_candidates(group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in group
        if str(row.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE
        and finite_number(row.get("mean_delta_vs_static_primary"), math.inf) <= -DEFAULT_MARGIN
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    decisions = read_csv_rows(resolve(args.context_decisions_csv, root))
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    grouped = grouped_contexts(dev_rows)
    decision_by_context = {str(row.get("normalized_context_key", "")): row for row in decisions}
    audit_rows: list[dict[str, Any]] = []
    selected_nonstatic = []
    oracle_captures = 0
    missed_helpful = 0
    harmful_selected = 0
    regrets = []

    for key, group in sorted(grouped.items()):
        decision = decision_by_context.get(key, {})
        selected_id = str(decision.get("selected_candidate_id", STATIC_FLOW_SHIELD_CANDIDATE))
        selected = select_candidate(group, selected_id)
        oracle = oracle_candidate(group)
        helpful = sorted(
            helpful_candidates(group),
            key=lambda row: (
                finite_number(row.get("mean_delta_vs_static_primary"), math.inf),
                str(row.get("candidate_id", "")),
            ),
        )
        best_helpful = helpful[0] if helpful else {}
        selected_delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
        selected_regret = finite_number(selected.get("oracle_regret_primary"), math.inf)
        regrets.append(selected_regret)
        selected_is_nonstatic = selected_id != STATIC_FLOW_SHIELD_CANDIDATE
        selected_nonstatic.append(selected_id) if selected_is_nonstatic else None
        oracle_capture = selected_id == str(oracle.get("candidate_id", ""))
        oracle_captures += 1 if oracle_capture else 0
        harmful = selected_is_nonstatic and selected_delta >= DEFAULT_MARGIN
        harmful_selected += 1 if harmful else 0
        missed = (not selected_is_nonstatic) and bool(helpful)
        missed_helpful += 1 if missed else 0
        audit_rows.append(
            {
                "normalized_context_key": key,
                "map": selected.get("map", ""),
                "map_family": map_family(str(selected.get("map", ""))),
                "agents": selected.get("agents", ""),
                "map_agent": f"{selected.get('map', '')}|a{selected.get('agents', '')}",
                "seed": selected.get("seed", ""),
                "selected_candidate_id": selected_id,
                "oracle_candidate_id": oracle.get("candidate_id", ""),
                "oracle_capture": oracle_capture,
                "selection_reason": decision.get("selection_reason", ""),
                "selected_delta_vs_static": selected_delta,
                "selected_delta_vs_additive": selected.get("mean_delta_vs_additive_primary", ""),
                "selected_regret_to_oracle": selected_regret,
                "selected_harmful_vs_static": harmful,
                "helpful_candidate_count": len(helpful),
                "best_helpful_candidate_id": best_helpful.get("candidate_id", ""),
                "best_helpful_delta_vs_static": best_helpful.get("mean_delta_vs_static_primary", ""),
                "missed_helpful_context": missed,
                "predicted_best_delta": decision.get("predicted_best_delta", ""),
                "predicted_best_harmful_risk": decision.get("predicted_best_harmful_risk", ""),
                "predicted_margin": decision.get("predicted_margin", ""),
            }
        )

    selected_distribution = count_by(audit_rows, "selected_candidate_id")
    nonstatic_distribution = dict(sorted(Counter(selected_nonstatic).items()))
    dominant_nonstatic = max(nonstatic_distribution.values()) / len(selected_nonstatic) if selected_nonstatic else 0.0
    mostly_slow_decay_specialist = (
        bool(selected_nonstatic)
        and nonstatic_distribution.get(SLOW_DECAY_HIGH_SHIELD_CANDIDATE, 0) / len(selected_nonstatic) >= 0.80
    )
    broad_multi_candidate_selector = len(nonstatic_distribution) >= 3 and dominant_nonstatic < 0.80
    flags = observed_id_flags(audit_rows)
    summary = {
        "schema_version": "phase5p5_repair5g513_g512_selection_audit_summary_v1",
        "decision": "g512_selection_audit_completed",
        "dev_contexts": len(audit_rows),
        "selected_candidate_distribution": selected_distribution,
        "selected_nonstatic_candidate_distribution": nonstatic_distribution,
        "selected_contexts_by_map_agent": count_by(audit_rows, "map_agent"),
        "selected_contexts_by_map_family": count_by(audit_rows, "map_family"),
        "oracle_capture_count": oracle_captures,
        "oracle_capture_rate": oracle_captures / len(audit_rows) if audit_rows else 0.0,
        "regret_to_oracle_mean": mean(regrets),
        "missed_helpful_contexts": missed_helpful,
        "harmful_selected_contexts": harmful_selected,
        "nonstatic_selection_count": len(selected_nonstatic),
        "dominant_nonstatic_selection_share": dominant_nonstatic,
        "mostly_safe_gated_slow_decay_high_shield": mostly_slow_decay_specialist,
        "broad_multi_candidate_selector": broad_multi_candidate_selector,
        "interpretation": (
            "mostly_safe_gated_slow_decay_high_shield"
            if mostly_slow_decay_specialist
            else "broader_multi_candidate_selector"
            if broad_multi_candidate_selector
            else "low_coverage_or_mixed_specialist"
        ),
        **flags,
        **G513_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), audit_rows)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.13 G5.12 Selection Audit\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- dev_contexts: `{len(audit_rows)}`\n"
        f"- selected_candidate_distribution: `{selected_distribution}`\n"
        f"- selected_nonstatic_candidate_distribution: `{nonstatic_distribution}`\n"
        f"- oracle_capture_count: `{oracle_captures}`\n"
        f"- oracle_capture_rate: `{summary['oracle_capture_rate']}`\n"
        f"- regret_to_oracle_mean: `{summary['regret_to_oracle_mean']}`\n"
        f"- missed_helpful_contexts: `{missed_helpful}`\n"
        f"- harmful_selected_contexts: `{harmful_selected}`\n"
        f"- broad_multi_candidate_selector: `{broad_multi_candidate_selector}`\n"
        f"- mostly_safe_gated_slow_decay_high_shield: `{mostly_slow_decay_specialist}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "This audit is context grouped. G5.12 selects a candidate in a dev context only after scoring all 14 candidates, otherwise it falls back to static flow-shield. "
        "The output table lists oracle captures, regret to oracle, missed helpful fallbacks, and harmful selected contexts for each dev context.\n",
    )
    print(json.dumps({"decision": summary["decision"], "dev_contexts": len(audit_rows), "oracle_capture_rate": summary["oracle_capture_rate"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
