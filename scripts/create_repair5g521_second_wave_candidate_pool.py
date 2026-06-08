"""Create the deterministic G5.21 second-wave bounded candidate pool."""

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

from repair5g521_common import (  # noqa: E402
    CandidateParams,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_TARGETS_CSV,
    G521_CLOSED_CLAIMS,
    G521_POOL_CSV,
    G521_POOL_REPORT,
    G521_POOL_SUMMARY,
    G521_SELECTED_CSV,
    boolish,
    candidate_param_dict,
    candidate_params,
    csv_number,
    family_for_candidate,
    finite_number,
    g518_retained_candidate_ids,
    g521_candidate_id,
    old14_candidate_ids,
    param_distance,
    read_rows,
    repo_root,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G520_TARGETS_CSV))
    parser.add_argument("--target-contexts-csv", type=Path, default=Path(G520_SECOND_WAVE_CONTEXTS_CSV))
    parser.add_argument("--pool-csv", type=Path, default=Path(G521_POOL_CSV))
    parser.add_argument("--selected-csv", type=Path, default=Path(G521_SELECTED_CSV))
    parser.add_argument("--report", type=Path, default=Path(G521_POOL_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_POOL_SUMMARY))
    return parser.parse_args(argv)


def add_candidate(rows: list[dict[str, Any]], seen: set[str], *, block: str, params: CandidateParams, purpose: str) -> None:
    candidate = g521_candidate_id(params)
    if candidate in seen:
        return
    seen.add(candidate)
    family = family_for_candidate(candidate, params)
    conservative = params.alpha_flow_wait_or_nonprogress <= 0.50 and params.flow_shield_beta <= 0.35 and params.max_flow_shield <= 0.75
    risky = params.alpha_cong_blocked >= 1.60 or params.flow_shield_beta >= 0.55 or params.max_flow_shield >= 0.90
    rows.append(
        {
            "candidate_id": candidate,
            "candidate_block": block,
            "candidate_family": family,
            "candidate_purpose": purpose,
            "expected_conservative_no_solution_risk_reducer": conservative,
            "expected_high_gain_risky": risky,
            **candidate_param_dict(candidate),
            **G521_CLOSED_CLAIMS,
        }
    )


def recurrent_winner_stats(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for row in targets:
        candidate = str(row.get("candidate_id", ""))
        if not candidate.startswith("repair5g518_grid_"):
            continue
        item = stats.setdefault(candidate, {"oracle_wins": 0, "safe_positive": 0, "target_context_hits": 0, "best_gap_sum": 0.0})
        item["oracle_wins"] += int(boolish(row.get("is_new22_oracle_winner")) or boolish(row.get("new_opportunity_candidate")))
        item["safe_positive"] += int(boolish(row.get("safe_new_candidate_positive")))
        if boolish(row.get("new_opportunity_context")):
            item["target_context_hits"] += 1
            item["best_gap_sum"] += finite_number(row.get("new_candidate_best_gap_vs_old14"), 0.0)
    return stats


def nearest(candidate: str, refs: list[str]) -> tuple[str, float]:
    params = candidate_params(candidate)
    best = ("", math.inf)
    for ref in refs:
        distance = param_distance(params, candidate_params(ref))
        if distance < best[1] or (distance == best[1] and ref < best[0]):
            best = (ref, distance)
    return best


def annotate(rows: list[dict[str, Any]], targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    root = repo_root()
    old_ids = old14_candidate_ids(root)
    retained = g518_retained_candidate_ids(limit=8)
    stats = recurrent_winner_stats(targets)
    out = []
    for row in rows:
        candidate = str(row["candidate_id"])
        nearest_g518, d_g518 = nearest(candidate, retained)
        nearest_old, d_old = nearest(candidate, old_ids)
        ref_stats = stats.get(nearest_g518, {})
        block_prior = {
            "block_A_block_heavy": 0.02,
            "block_B_high_beta": 0.015,
            "block_C_wait_conservative": 0.018,
            "block_D_decay_shield_ablation": 0.012,
        }.get(str(row.get("candidate_block")), 0.0)
        score = (
            d_g518
            - 0.010 * float(ref_stats.get("oracle_wins", 0))
            - 0.002 * float(ref_stats.get("safe_positive", 0))
            - block_prior
            + 0.001 * d_old
        )
        out.append(
            {
                **row,
                "nearest_g518_winner": nearest_g518,
                "nearest_g518_param_distance": csv_number(d_g518),
                "nearest_old14_candidate": nearest_old,
                "nearest_old14_param_distance": csv_number(d_old),
                "nearest_g518_oracle_wins": ref_stats.get("oracle_wins", 0),
                "nearest_g518_safe_positive_rows": ref_stats.get("safe_positive", 0),
                "nearest_g518_target_context_hits": ref_stats.get("target_context_hits", 0),
                "predeclared_selection_score": csv_number(score),
                "uses_g521_solver_outcome": False,
            }
        )
    return out


def raw_pool() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for b in [1.40, 1.50, 1.65]:
        for w in [0.40, 0.45, 0.55]:
            for dc in [0.90, 0.95]:
                for beta in [0.35, 0.45, 0.50]:
                    add_candidate(
                        rows,
                        seen,
                        block="block_A_block_heavy",
                        params=CandidateParams(0.90, b, 1.00, w, dc, 1.00, beta, 0.75, False),
                        purpose="block-heavy low-c high-block neighborhood",
                    )
    for b in [1.15, 1.25, 1.35]:
        for beta in [0.55, 0.60, 0.65]:
            for max_shield in [0.75, 0.90]:
                add_candidate(
                    rows,
                    seen,
                    block="block_B_high_beta",
                    params=CandidateParams(1.20, b, 1.00, 0.70, 0.95, 1.00, beta, max_shield, False),
                    purpose="high-beta high-wait high-flow neighborhood",
                )
    for w in [0.35, 0.40, 0.50]:
        for beta in [0.30, 0.35]:
            for dc in [0.90, 0.95]:
                add_candidate(
                    rows,
                    seen,
                    block="block_C_wait_conservative",
                    params=CandidateParams(1.25, 1.25, 1.00, w, dc, 1.00, beta, 0.75, False),
                    purpose="wait-conservative low-beta neighborhood",
                )
    for dc in [0.90, 0.95, 1.00]:
        for df in [0.90, 0.95, 1.00]:
            for beta in [0.35, 0.45, 0.55]:
                for max_shield in [0.60, 0.75, 0.90]:
                    add_candidate(
                        rows,
                        seen,
                        block="block_D_decay_shield_ablation",
                        params=CandidateParams(1.25, 1.25, 1.00, 0.75, dc, df, beta, max_shield, False),
                        purpose="decay and shield ablation neighborhood",
                    )
    return rows


def select_candidates(pool: list[dict[str, Any]], limit: int = 16) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    blocks = [
        "block_A_block_heavy",
        "block_B_high_beta",
        "block_C_wait_conservative",
        "block_D_decay_shield_ablation",
    ]
    for block in blocks:
        block_rows = [row for row in pool if row.get("candidate_block") == block]
        ranked = sorted(block_rows, key=lambda row: (finite_number(row.get("predeclared_selection_score"), math.inf), str(row.get("candidate_id", ""))))
        selected.extend(ranked[:4])
    selected = selected[:limit]
    for index, row in enumerate(selected):
        row["selected_for_execution"] = True
        row["selection_rank"] = index + 1
    return selected


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = read_rows(args.targets_csv)
    target_contexts = read_rows(args.target_contexts_csv)
    pool = annotate(raw_pool(), targets)
    selected = select_candidates(pool, limit=16)
    selected_ids = {str(row.get("candidate_id", "")) for row in selected}
    for row in pool:
        row["selected_for_execution"] = str(row.get("candidate_id", "")) in selected_ids
    block_counts = {block: sum(1 for row in selected if row.get("candidate_block") == block) for block in sorted({str(row.get("candidate_block", "")) for row in pool})}
    conservative_count = sum(1 for row in selected if boolish(row.get("expected_conservative_no_solution_risk_reducer")))
    risky_count = sum(1 for row in selected if boolish(row.get("expected_high_gain_risky")))
    gates = {
        "raw_pool_count_ge_48": len(pool) >= 48,
        "selected_count_le_16": len(selected) <= 16,
        "selected_count_eq_16": len(selected) == 16,
        "at_least_3_per_block": all(count >= 3 for count in block_counts.values()),
        "conservative_candidates_ge_2": conservative_count >= 2,
        "risky_candidates_ge_2": risky_count >= 2,
        "target_contexts_eq_16": len(target_contexts) == 16,
        "no_g521_solver_outcome_used": all(not boolish(row.get("uses_g521_solver_outcome")) for row in pool),
    }
    decision = "second_wave_candidate_pool_passed_continue_adapter_grammar" if all(gates.values()) else "second_wave_candidate_pool_failed"
    summary = {
        "schema_version": "phase5p5_repair5g521_second_wave_candidate_pool_summary_v1",
        "decision": decision,
        "raw_pool_count": len(pool),
        "selected_candidate_count": len(selected),
        "selected_block_counts": block_counts,
        "conservative_selected_count": conservative_count,
        "risky_selected_count": risky_count,
        "target_context_count": len(target_contexts),
        "gates": gates,
        **G521_CLOSED_CLAIMS,
    }
    write_rows(args.pool_csv, pool)
    write_rows(args.selected_csv, selected)
    write_json_file(args.summary_json, summary)
    block_lines = "\n".join(f"- {block}: `{count}` selected" for block, count in block_counts.items())
    write_text_file(
        args.report,
        "# Repair5G.5.21 Second-Wave Candidate Pool\n\n"
        f"- decision: `{decision}`\n"
        f"- raw_pool_count: `{len(pool)}`\n"
        f"- selected_candidate_count: `{len(selected)}`\n"
        f"- conservative_selected_count: `{conservative_count}`\n"
        f"- risky_selected_count: `{risky_count}`\n"
        f"- target_context_count: `{len(target_contexts)}`\n"
        f"- gates: `{gates}`\n\n"
        "## Selected Blocks\n\n"
        f"{block_lines}\n\n"
        "Selection is deterministic and uses only G5.18/G5.20 recurrent-winner metadata plus parameter-distance diversity. No G5.21 solver outcome is used.\n",
    )
    print(json.dumps({"decision": decision, "raw_pool_count": len(pool), "selected_candidate_count": len(selected)}))
    return 0 if decision != "second_wave_candidate_pool_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
