"""Create G5.12 candidate-level regret/ranking targets from the G5.11 lattice."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    C_ONLY_CANDIDATE,
    CLOSED_CLAIMS,
    DEFAULT_MARGIN,
    PRIMARY_BUDGETS_MS,
    STATIC_ABSTAIN_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    context_key,
    count_by,
    csv_number,
    finite_number,
    group_rows_by_context,
    mean,
    observed_id_flags,
    ranking,
    read_csv_rows,
    repo_root,
    resolve,
    score_from_probe,
    split_for_seed,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_candidate_regret_targets.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_candidate_regret_targets_summary.json"
PARAM_COLUMNS = [
    "alpha_cong_committed",
    "alpha_cong_blocked",
    "alpha_flow_progress",
    "alpha_flow_wait_or_nonprogress",
    "rho_cong",
    "rho_flow",
    "flow_shield_beta",
    "max_flow_shield",
    "static_fallback",
    "additive_fallback",
    "c_only_f_disabled",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def candidate_meta(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    out = {}
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if candidate:
            out[candidate] = row
    return out


def budget_rows_for_context(rows: list[dict[str, object]]) -> dict[int, dict[str, dict[str, object]]]:
    grouped: dict[int, dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        budget = int(finite_number(row.get("short_budget_ms"), -1))
        candidate = str(row.get("candidate_id", ""))
        if budget and candidate:
            old = grouped[budget].get(candidate)
            if old is None or score_from_probe(row) < score_from_probe(old):
                grouped[budget][candidate] = row
    return grouped


def penalized_scores(scores: dict[str, float]) -> dict[str, float]:
    finite = [value for value in scores.values() if math.isfinite(value)]
    penalty = (max(finite) + 1.0) if finite else 1.0e6
    return {key: value if math.isfinite(value) else penalty for key, value in scores.items()}


def label_for(candidate_id: str, meta: dict[str, object], mean_delta: float) -> str:
    if boolish(meta.get("static_fallback")) or candidate_id in {STATIC_FLOW_SHIELD_CANDIDATE, STATIC_ABSTAIN_CANDIDATE}:
        return "static_fallback_candidate"
    if boolish(meta.get("additive_fallback")) or candidate_id == ADDITIVE_CANDIDATE:
        return "additive_bad_baseline"
    if boolish(meta.get("c_only_f_disabled")) or candidate_id == C_ONLY_CANDIDATE:
        return "c_only_ablation_candidate"
    if mean_delta <= -DEFAULT_MARGIN:
        return "helpful_parameter_candidate"
    if mean_delta >= DEFAULT_MARGIN:
        return "harmful_parameter_candidate"
    return "neutral_parameter_candidate"


def target_weight(candidate_id: str, meta: dict[str, object], label: str) -> float:
    if label == "static_fallback_candidate" or candidate_id in {STATIC_FLOW_SHIELD_CANDIDATE, STATIC_ABSTAIN_CANDIDATE}:
        return 0.5
    if boolish(meta.get("additive_fallback")) or boolish(meta.get("c_only_f_disabled")):
        return 1.0
    return 1.0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    results = read_csv_rows(resolve(args.results_csv, root))
    candidates = read_csv_rows(resolve(args.candidate_csv, root))
    meta_by_candidate = candidate_meta(candidates)
    candidate_ids = [str(row["candidate_id"]) for row in candidates if str(row.get("candidate_id", ""))]
    grouped = group_rows_by_context(results)
    flags = observed_id_flags(results)
    out_rows: list[dict[str, object]] = []
    infeasible_primary_cells = 0

    for context_id, (key, context_rows) in enumerate(sorted(grouped.items()), start=1):
        sample = context_rows[0]
        by_budget = budget_rows_for_context(context_rows)
        raw_scores_by_budget: dict[int, dict[str, float]] = {}
        scores_by_budget: dict[int, dict[str, float]] = {}
        rows_by_budget_candidate: dict[tuple[int, str], dict[str, object]] = {}
        for budget in PRIMARY_BUDGETS_MS:
            raw = {candidate: score_from_probe(by_budget.get(budget, {}).get(candidate, {})) for candidate in candidate_ids}
            infeasible_primary_cells += sum(1 for value in raw.values() if not math.isfinite(value))
            raw_scores_by_budget[budget] = raw
            scores_by_budget[budget] = penalized_scores(raw)
            for candidate in candidate_ids:
                rows_by_budget_candidate[(budget, candidate)] = by_budget.get(budget, {}).get(candidate, {})

        static_scores = {budget: scores_by_budget[budget][STATIC_FLOW_SHIELD_CANDIDATE] for budget in PRIMARY_BUDGETS_MS}
        additive_scores = {budget: scores_by_budget[budget][ADDITIVE_CANDIDATE] for budget in PRIMARY_BUDGETS_MS}
        mean_scores = {
            candidate: mean(scores_by_budget[budget][candidate] for budget in PRIMARY_BUDGETS_MS)
            for candidate in candidate_ids
        }
        ranks = ranking(mean_scores)
        oracle_candidate = min(mean_scores, key=lambda candidate: (mean_scores[candidate], candidate))
        oracle_score = mean_scores[oracle_candidate]

        for candidate in candidate_ids:
            meta = meta_by_candidate[candidate]
            score_1000 = scores_by_budget[1000][candidate]
            score_2000 = scores_by_budget[2000][candidate]
            raw_1000 = raw_scores_by_budget[1000][candidate]
            raw_2000 = raw_scores_by_budget[2000][candidate]
            delta_static_1000 = score_1000 - static_scores[1000]
            delta_static_2000 = score_2000 - static_scores[2000]
            mean_delta_static = mean([delta_static_1000, delta_static_2000])
            mean_delta_additive = mean(
                [
                    score_1000 - additive_scores[1000],
                    score_2000 - additive_scores[2000],
                ]
            )
            label = label_for(candidate, meta, mean_delta_static)
            row_1000 = rows_by_budget_candidate[(1000, candidate)]
            row_2000 = rows_by_budget_candidate[(2000, candidate)]
            trace_event_count = int(
                finite_number(
                    row_1000.get("trace_event_count", row_2000.get("trace_event_count", sample.get("trace_event_count", 0))),
                    0.0,
                )
            )
            seed = int(finite_number(sample.get("seed"), 0.0))
            out_rows.append(
                {
                    "context_id": context_id,
                    "normalized_context_key": key,
                    "map": sample.get("map", ""),
                    "agents": int(finite_number(sample.get("agents"), 0.0)),
                    "seed": seed,
                    "iteration": int(finite_number(sample.get("iteration"), 0.0)),
                    "trace_event_count": trace_event_count,
                    "traffic_before_hash_full": sample.get("traffic_before_hash_full", ""),
                    "candidate_id": candidate,
                    "candidate_index": int(finite_number(meta.get("candidate_index"), 0.0)),
                    "alpha_cong_committed": csv_number(finite_number(meta.get("alpha_cong_committed"), 0.0)),
                    "alpha_cong_blocked": csv_number(finite_number(meta.get("alpha_cong_blocked"), 0.0)),
                    "alpha_flow_progress": csv_number(finite_number(meta.get("alpha_flow_progress"), 0.0)),
                    "alpha_flow_wait_or_nonprogress": csv_number(finite_number(meta.get("alpha_flow_wait_or_nonprogress"), 0.0)),
                    "rho_cong": csv_number(finite_number(meta.get("rho_cong"), 0.0)),
                    "rho_flow": csv_number(finite_number(meta.get("rho_flow"), 0.0)),
                    "flow_shield_beta": csv_number(finite_number(meta.get("flow_shield_beta"), 0.0)),
                    "max_flow_shield": csv_number(finite_number(meta.get("max_flow_shield"), 0.0)),
                    "static_fallback": boolish(meta.get("static_fallback")),
                    "additive_fallback": boolish(meta.get("additive_fallback")),
                    "c_only_f_disabled": boolish(meta.get("c_only_f_disabled")),
                    "score_1000": csv_number(score_1000),
                    "score_2000": csv_number(score_2000),
                    "score_1000_penalized_infeasible": not math.isfinite(raw_1000),
                    "score_2000_penalized_infeasible": not math.isfinite(raw_2000),
                    "static_score_1000": csv_number(static_scores[1000]),
                    "static_score_2000": csv_number(static_scores[2000]),
                    "additive_score_1000": csv_number(additive_scores[1000]),
                    "additive_score_2000": csv_number(additive_scores[2000]),
                    "delta_vs_static_1000": csv_number(delta_static_1000),
                    "delta_vs_static_2000": csv_number(delta_static_2000),
                    "mean_delta_vs_static_primary": csv_number(mean_delta_static),
                    "mean_delta_vs_additive_primary": csv_number(mean_delta_additive),
                    "oracle_regret_primary": csv_number(mean_scores[candidate] - oracle_score),
                    "rank_primary": ranks[candidate],
                    "helpful_vs_static": (not boolish(meta.get("static_fallback"))) and (not boolish(meta.get("additive_fallback"))) and mean_delta_static <= -DEFAULT_MARGIN,
                    "harmful_vs_static": (not boolish(meta.get("static_fallback"))) and (not boolish(meta.get("additive_fallback"))) and mean_delta_static >= DEFAULT_MARGIN,
                    "near_static_neutral": abs(mean_delta_static) < DEFAULT_MARGIN,
                    "label_class": label,
                    "oracle_candidate_for_context": oracle_candidate,
                    "target_weight": target_weight(candidate, meta, label),
                    "split": split_for_seed(seed),
                    "observed_ids_only": flags["observed_ids_only"],
                    "ids_166_205_untouched": flags["ids_166_205_untouched"],
                }
            )

    write_csv_rows(resolve(args.output_csv, root), out_rows)
    label_counts = count_by(out_rows, "label_class")
    contexts = {str(row["normalized_context_key"]) for row in out_rows}
    static_duplicate_contexts = sum(
        1
        for key in contexts
        if {row["candidate_id"] for row in out_rows if row["normalized_context_key"] == key}
        >= {STATIC_FLOW_SHIELD_CANDIDATE, STATIC_ABSTAIN_CANDIDATE}
    )
    gates = {
        "candidate_level_rows_ge_840": len(out_rows) >= 840,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_14": len(candidate_ids) == 14,
        "helpful_count_gt_0": label_counts.get("helpful_parameter_candidate", 0) > 0,
        "harmful_count_gt_0": label_counts.get("harmful_parameter_candidate", 0) > 0,
        "neutral_or_static_count_gt_0": label_counts.get("neutral_parameter_candidate", 0) + label_counts.get("static_fallback_candidate", 0) > 0,
        "additive_bad_count_gt_0": label_counts.get("additive_bad_baseline", 0) > 0,
        "static_alias_duplicate_contexts_reported": static_duplicate_contexts >= 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    decision = "candidate_regret_targets_passed_continue_feature_v3" if all(gates.values()) else "candidate_regret_targets_failed"
    summary = {
        "schema_version": "phase5p5_repair5g512_candidate_regret_targets_summary_v1",
        "decision": decision,
        "candidate_level_rows": len(out_rows),
        "contexts": len(contexts),
        "candidates": len(candidate_ids),
        "label_counts": label_counts,
        "helpful_count": label_counts.get("helpful_parameter_candidate", 0),
        "harmful_count": label_counts.get("harmful_parameter_candidate", 0),
        "neutral_or_static_count": label_counts.get("neutral_parameter_candidate", 0) + label_counts.get("static_fallback_candidate", 0),
        "additive_bad_count": label_counts.get("additive_bad_baseline", 0),
        "static_alias_duplicate_contexts": static_duplicate_contexts,
        "static_alias_target_weight_policy": "split_static_alias_weight_0p5_each",
        "infeasible_primary_score_cells_penalized": infeasible_primary_cells,
        "targets_csv": str(resolve(args.output_csv, root)),
        "gates": gates,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Candidate Regret Targets\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate_level_rows: `{len(out_rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidates: `{len(candidate_ids)}`\n"
        f"- label_counts: `{label_counts}`\n"
        f"- static_alias_duplicate_contexts: `{static_duplicate_contexts}`\n"
        f"- static_alias_target_weight_policy: `split_static_alias_weight_0p5_each`\n"
        f"- infeasible_primary_score_cells_penalized: `{infeasible_primary_cells}`\n"
        f"- gates: `{gates}`\n\n"
        "Each row is one context-candidate pair aggregated over the 1000ms and 2000ms primary budgets. "
        "Lower SoL ratio is better, deltas are candidate minus baseline, and candidate ranks are grouped within context. "
        "Static aliases are retained for the required 60 x 14 artifact shape but weighted at 0.5 each so they do not silently double static training mass.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(out_rows), "contexts": len(contexts)}))
    return 0 if decision != "candidate_regret_targets_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
