"""Create the Repair5G.5.16 error bank from G5.15 decisions and safety diagnostics."""

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

from repair5g512_common import DEFAULT_MARGIN, finite_number, observed_id_flags, read_csv_rows, read_json, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g513_common import grouped_contexts, select_candidate  # noqa: E402
from repair5g516_common import (  # noqa: E402
    DEFAULT_G515_CONTEXT_DECISIONS,
    DEFAULT_G515_FALSE_POSITIVE_SUMMARY,
    DEFAULT_G515_SAFETY_SUMMARY,
    DEFAULT_G515_V5_MATRIX,
    DEFAULT_G516_ERROR_BANK,
    DEFAULT_G516_ERROR_BANK_SUMMARY,
    G516_CLOSED_CLAIMS,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_error_bank.md"
CATEGORY_WEIGHTS = {
    "harmful_false_positive": 3.0,
    "missed_helpful_fallback": 2.0,
    "static_near_oracle": 1.5,
    "high_uncertainty": 1.25,
    "oracle_gap_high": 1.5,
    "candidate_disagreement": 1.0,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_G515_V5_MATRIX))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_G515_CONTEXT_DECISIONS))
    parser.add_argument("--false-positive-summary", type=Path, default=Path(DEFAULT_G515_FALSE_POSITIVE_SUMMARY))
    parser.add_argument("--safety-summary", type=Path, default=Path(DEFAULT_G515_SAFETY_SUMMARY))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_G516_ERROR_BANK))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_G516_ERROR_BANK_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def full_key_for_prefix(groups: dict[str, list[dict[str, Any]]], prefix: str) -> str:
    for key in sorted(groups):
        if key.startswith(prefix):
            return key
    return prefix


def context_base_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    return select_candidate(group, "repair5g59_static_flow_shield") if group else {}


def add_error_row(
    out: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    *,
    category: str,
    key: str,
    groups: dict[str, list[dict[str, Any]]],
    source: str,
    note: str,
    selected_candidate_id: str = "",
) -> None:
    if (category, key) in seen:
        return
    seen.add((category, key))
    group = groups.get(key, [])
    base = context_base_row(group)
    oracle_id = str(base.get("oracle_candidate_for_context", ""))
    oracle = select_candidate(group, oracle_id) if group else {}
    static = select_candidate(group, "repair5g59_static_flow_shield") if group else {}
    selected = select_candidate(group, selected_candidate_id) if group and selected_candidate_id else {}
    out.append(
        {
            "row_type": "error_bank_context",
            "normalized_context_key": key,
            "map": base.get("map", ""),
            "agents": base.get("agents", ""),
            "seed": base.get("seed", ""),
            "iteration": base.get("iteration", ""),
            "error_category": category,
            "source": source,
            "error_weight": CATEGORY_WEIGHTS.get(category, 1.0),
            "oracle_candidate_for_context": oracle_id,
            "oracle_delta_vs_static": oracle.get("mean_delta_vs_static_primary", ""),
            "static_oracle_regret_primary": static.get("oracle_regret_primary", ""),
            "selected_candidate_id": selected_candidate_id,
            "selected_delta_vs_static": selected.get("mean_delta_vs_static_primary", ""),
            "candidate_count": len(group),
            "observed_ids_only": True,
            "ids_166_205_untouched": True,
            "note": note,
        }
    )


def disagreement_contexts(context_rows: list[dict[str, Any]]) -> list[str]:
    by_key: dict[str, dict[str, str]] = defaultdict(dict)
    for row in context_rows:
        if row.get("eval_scope") != "oof":
            continue
        policy = str(row.get("policy", ""))
        if policy in {"two_stage_safety_ranker", "pairwise_context_ranker", "v4_g514_ranker_reproduced", "safe_train_only_map_agent_gate"}:
            by_key[str(row.get("normalized_context_key", ""))][policy] = str(row.get("selected_candidate_id", ""))
    out = []
    for key, choices in sorted(by_key.items()):
        if len(set(choices.values())) > 1:
            out.append(key)
    return out


def high_gap_contexts(groups: dict[str, list[dict[str, Any]]], *, limit: int = 20) -> list[str]:
    scored = []
    for key, group in groups.items():
        static = select_candidate(group, "repair5g59_static_flow_shield")
        regret = finite_number(static.get("oracle_regret_primary"), math.inf)
        oracle_id = str(static.get("oracle_candidate_for_context", ""))
        oracle = select_candidate(group, oracle_id)
        oracle_delta = finite_number(oracle.get("mean_delta_vs_static_primary"), math.inf)
        if math.isfinite(regret) and regret > DEFAULT_MARGIN and oracle_delta <= -DEFAULT_MARGIN:
            scored.append((regret, key))
    return [key for _, key in sorted(scored, reverse=True)[:limit]]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    context_rows = read_csv_rows(resolve(args.context_decisions_csv, root))
    fp_summary = read_json(resolve(args.false_positive_summary, root))
    safety = read_json(resolve(args.safety_summary, root))
    groups = grouped_contexts(rows)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for key in safety.get("harmful_false_positive_context_keys", []):
        add_error_row(
            out,
            seen,
            category="harmful_false_positive",
            key=str(key),
            groups=groups,
            source="g515_static_abstention_safety_update",
            note="G5.15 primary selected a nonstatic candidate that was harmful versus static.",
        )
    for item in fp_summary.get("autopsy_rows", []):
        prefix = str(item.get("context_prefix", ""))
        key = full_key_for_prefix(groups, prefix)
        add_error_row(
            out,
            seen,
            category="harmful_false_positive",
            key=key,
            groups=groups,
            source="g515_false_positive_autopsy",
            note=str(item.get("risk_underprediction_reason", "autopsy target")),
            selected_candidate_id=str(item.get("selected_candidate", "")),
        )
    for key in safety.get("missed_helpful_context_keys", []):
        add_error_row(
            out,
            seen,
            category="missed_helpful_fallback",
            key=str(key),
            groups=groups,
            source="g515_static_abstention_safety_update",
            note="G5.15 fell back to static while a nonstatic candidate had useful oracle gap.",
        )
    for key in safety.get("static_near_oracle_context_keys", []):
        add_error_row(
            out,
            seen,
            category="static_near_oracle",
            key=str(key),
            groups=groups,
            source="g515_static_abstention_safety_update",
            note="Static is near the best observed candidate; use as abstention boundary evidence.",
        )
    for key in safety.get("high_uncertainty_context_keys", []):
        add_error_row(
            out,
            seen,
            category="high_uncertainty",
            key=str(key),
            groups=groups,
            source="g515_static_abstention_safety_update",
            note="G5.15 predicted margin or risk placed this context in an uncertainty band.",
        )
    for key in high_gap_contexts(groups):
        add_error_row(
            out,
            seen,
            category="oracle_gap_high",
            key=key,
            groups=groups,
            source="g515_v5_matrix",
            note="Static regret to the best observed candidate is high enough to justify local opportunity analysis.",
        )
    for key in disagreement_contexts(context_rows):
        add_error_row(
            out,
            seen,
            category="candidate_disagreement",
            key=key,
            groups=groups,
            source="g515_oof_context_decisions",
            note="G5.15 policies or controls disagree on the selected candidate.",
        )

    flags = observed_id_flags(out)
    counts = Counter(str(row.get("error_category", "")) for row in out)
    gates = {
        "error_bank_rows_gt_0": len(out) > 0,
        "harmful_fp_count_ge_2": counts.get("harmful_false_positive", 0) >= 2,
        "missed_helpful_count_gt_0": counts.get("missed_helpful_fallback", 0) > 0,
        "static_near_oracle_count_ge_8": counts.get("static_near_oracle", 0) >= 8,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    decision = "error_bank_created_continue_lattice" if all(gates.values()) else "error_bank_gate_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g516_error_bank_summary_v1",
        "decision": decision,
        "error_bank_rows": len(out),
        "category_counts": dict(sorted(counts.items())),
        "harmful_fp_count": counts.get("harmful_false_positive", 0),
        "missed_helpful_count": counts.get("missed_helpful_fallback", 0),
        "static_near_oracle_count": counts.get("static_near_oracle", 0),
        "high_uncertainty_count": counts.get("high_uncertainty", 0),
        "gates": gates,
        **flags,
        **G516_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), out)
    write_json(resolve(args.summary_json, root), summary)
    category_lines = "\n".join(f"- {key}: `{value}`" for key, value in sorted(counts.items()))
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Error Bank\n\n"
        f"- decision: `{decision}`\n"
        f"- error_bank_rows: `{len(out)}`\n"
        f"- gates: `{gates}`\n\n"
        "## Category Counts\n\n"
        f"{category_lines}\n\n"
        "The bank is built only from observed G5.15/G5.11-G5.12-era table artifacts and does not use reserved IDs or runtime claims.\n",
    )
    print(json.dumps({"decision": decision, "error_bank_rows": len(out), "category_counts": dict(counts)}))
    return 0 if decision != "error_bank_gate_failed_stop" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
