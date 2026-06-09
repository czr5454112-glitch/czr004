"""Analyze Repair5G.5.10 executable lattice oracle gap."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import (  # noqa: E402
    G510_ADDITIVE_CANDIDATE,
    G510_DEFAULT_MARGIN,
    G510_PRIMARY_BUDGETS_MS,
    G510_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    as_jsonable,
    best_candidate,
    budget_key,
    candidate_scores_by_context_budget,
    context_key,
    finite_number,
    lattice_candidate_ids,
    map_agent_key,
    mean,
    read_csv_rows,
    repo_root,
    resolve,
    score_for_candidate,
    score_from_probe,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_CONTEXT_TABLE = "outputs/tables/phase5p5_repair5g510_lattice_oracle_by_context.csv"
DEFAULT_CANDIDATE_TABLE = "outputs/tables/phase5p5_repair5g510_lattice_candidate_distribution.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_lattice_counterfactual_analysis.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_lattice_counterfactual_analysis_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--context-table-csv", type=Path, default=Path(DEFAULT_CONTEXT_TABLE))
    parser.add_argument("--candidate-table-csv", type=Path, default=Path(DEFAULT_CANDIDATE_TABLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def g58_context_lookup(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    out = {}
    for row in rows:
        out[context_key(row)] = row
    return out


def classify_primary_context(
    key: str,
    by_budget: dict[float, dict[str, dict[str, object]]],
    g58_by_key: dict[str, dict[str, object]],
) -> dict[str, object]:
    row: dict[str, object] = {"normalized_context_key": key}
    budget_summaries: dict[float, dict[str, object]] = {}
    for budget in G510_PRIMARY_BUDGETS_MS:
        scores = by_budget.get(budget, {})
        oracle_id, oracle_score = best_candidate(scores)
        static_score = score_for_candidate(scores, G510_STATIC_CANDIDATE)
        additive_score = score_for_candidate(scores, G510_ADDITIVE_CANDIDATE)
        finite_count = sum(1 for probe in scores.values() if math.isfinite(score_from_probe(probe)))
        budget_summaries[budget] = {
            "oracle_candidate_id": oracle_id,
            "oracle_score": oracle_score,
            "static_score": static_score,
            "additive_score": additive_score,
            "finite_candidate_count": finite_count,
        }
        suffix = str(int(budget))
        row[f"oracle_{suffix}"] = oracle_id
        row[f"oracle_score_{suffix}"] = as_jsonable(oracle_score)
        row[f"static_score_{suffix}"] = as_jsonable(static_score)
        row[f"additive_score_{suffix}"] = as_jsonable(additive_score)
        row[f"finite_candidates_{suffix}"] = finite_count
        row[f"oracle_gap_over_static_{suffix}"] = as_jsonable(oracle_score - static_score if math.isfinite(oracle_score) and math.isfinite(static_score) else math.inf)
        row[f"oracle_gap_over_additive_{suffix}"] = as_jsonable(oracle_score - additive_score if math.isfinite(oracle_score) and math.isfinite(additive_score) else math.inf)
        old = g58_by_key.get(key, {})
        old_score = finite_number(old.get(f"oracle_score_{suffix}"), math.inf)
        row[f"oracle_gap_vs_g58_{suffix}"] = as_jsonable(oracle_score - old_score if math.isfinite(oracle_score) and math.isfinite(old_score) else math.inf)

    b1000 = budget_summaries[1000.0]
    b2000 = budget_summaries[2000.0]
    row["primary_1000_2000_measured"] = bool(b1000["finite_candidate_count"] or b2000["finite_candidate_count"])
    row["primary_1000_2000_stable"] = (
        bool(b1000["oracle_candidate_id"])
        and b1000["oracle_candidate_id"] == b2000["oracle_candidate_id"]
        and b1000["finite_candidate_count"] == b2000["finite_candidate_count"]
    )
    row["label_class_hint"] = (
        "stable_high_confidence_parameter_candidate"
        if row["primary_1000_2000_stable"] and b1000["oracle_candidate_id"] != G510_STATIC_CANDIDATE
        else "stable_static"
        if row["primary_1000_2000_stable"]
        else "budget_sensitive_exclude"
    )
    old = g58_by_key.get(key, {})
    for field in ["map", "agents", "seed", "iteration", "traffic_before_hash_full"]:
        row[field] = old.get(field, "")
    return row


def candidate_distribution(rows: list[dict[str, object]], lattice_ids: set[str]) -> list[dict[str, object]]:
    by_candidate: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if candidate in lattice_ids:
            by_candidate[candidate].append(row)
    out = []
    for candidate in sorted(lattice_ids):
        group = by_candidate.get(candidate, [])
        static_compared = [
            finite_number(row.get("delta_vs_static_in_same_context"), math.nan)
            for row in group
        ]
        finite_deltas = [value for value in static_compared if math.isfinite(value)]
        harmful = [value for value in finite_deltas if value > G510_DEFAULT_MARGIN]
        helpful = [value for value in finite_deltas if value < -G510_DEFAULT_MARGIN]
        out.append(
            {
                "candidate_id": candidate,
                "rows": len(group),
                "finite_rows": sum(1 for row in group if math.isfinite(score_from_probe(row))),
                "mean_score": as_jsonable(mean(score_from_probe(row) for row in group)),
                "mean_delta_vs_static": as_jsonable(mean(finite_deltas)),
                "harmful_vs_static_count": len(harmful),
                "harmful_vs_static_rate": len(harmful) / len(finite_deltas) if finite_deltas else "",
                "helpful_vs_static_count": len(helpful),
                "helpful_vs_static_rate": len(helpful) / len(finite_deltas) if finite_deltas else "",
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.results_csv, root))
    lattice_ids = set(lattice_candidate_ids(resolve(args.candidate_csv, root)))
    lattice_rows = [row for row in rows if str(row.get("candidate_id", "")) in lattice_ids]
    g58_by_key = g58_context_lookup(read_csv_rows(resolve(args.contexts_csv, root)))
    grouped = candidate_scores_by_context_budget(lattice_rows, allowed_candidates=lattice_ids)
    by_context: dict[str, dict[float, dict[str, dict[str, object]]]] = defaultdict(dict)
    for (key, budget), scores in grouped.items():
        by_context[key][budget] = scores

    context_rows = [
        classify_primary_context(key, budgets, g58_by_key)
        for key, budgets in sorted(by_context.items())
    ]
    write_csv_rows(resolve(args.context_table_csv, root), context_rows)
    candidate_rows = candidate_distribution(lattice_rows, lattice_ids)
    write_csv_rows(resolve(args.candidate_table_csv, root), candidate_rows)

    primary_rows = [row for row in context_rows if row.get("primary_1000_2000_measured")]
    stable_rows = [row for row in primary_rows if str(row.get("primary_1000_2000_stable")).lower() == "true"]
    measured_contexts = len(context_rows)
    later_iteration_contexts = sum(1 for row in context_rows if finite_number(row.get("iteration"), 0.0) > 0)
    oracle_wins = Counter(row.get("oracle_1000", "") for row in primary_rows if row.get("oracle_1000"))
    per_map_agent: dict[str, Counter[str]] = defaultdict(Counter)
    for row in primary_rows:
        per_map_agent[map_agent_key(row)][str(row.get("oracle_1000", ""))] += 1

    gaps_static = [finite_number(row.get("oracle_gap_over_static_1000"), math.inf) for row in primary_rows]
    gaps_additive = [finite_number(row.get("oracle_gap_over_additive_1000"), math.inf) for row in primary_rows]
    gaps_g58 = [finite_number(row.get("oracle_gap_vs_g58_1000"), math.inf) for row in primary_rows]
    beats_static = [value for value in gaps_static if math.isfinite(value) and value < -G510_DEFAULT_MARGIN]
    beats_additive = [value for value in gaps_additive if math.isfinite(value) and value < -G510_DEFAULT_MARGIN]
    finite_static = [value for value in gaps_static if math.isfinite(value)]
    finite_additive = [value for value in gaps_additive if math.isfinite(value)]
    finite_g58 = [value for value in gaps_g58 if math.isfinite(value)]
    no_solution_rows = sum(1 for row in lattice_rows if not math.isfinite(score_from_probe(row)))
    complete_primary_contexts = sum(
        1
        for key, budgets in by_context.items()
        if all(float(budget) in budgets and lattice_ids <= set(budgets[float(budget)]) for budget in G510_PRIMARY_BUDGETS_MS)
    )
    best_single = min(
        candidate_rows,
        key=lambda row: (finite_number(row.get("mean_score"), math.inf), str(row.get("candidate_id", ""))),
    ) if candidate_rows else {}
    candidate_space_oracle_gap_vs_g58 = mean(finite_g58)
    candidate_space_improves_g58 = math.isfinite(candidate_space_oracle_gap_vs_g58) and candidate_space_oracle_gap_vs_g58 < -G510_DEFAULT_MARGIN
    gates = {
        "candidate_space_oracle_gap_vs_g58_reported": math.isfinite(candidate_space_oracle_gap_vs_g58),
        "measured_contexts_ge_60": measured_contexts >= 60,
        "primary_1000_2000_stable_contexts_ge_40": len(stable_rows) >= 40,
        "complete_primary_contexts_ge_60": complete_primary_contexts >= 60,
        "oracle_beats_static_fraction_reported": bool(finite_static),
        "oracle_beats_additive_fraction_reported": bool(finite_additive),
        "observed_ids_only": all(int(finite_number(row.get("seed"), 0.0)) <= 165 for row in lattice_rows),
        "ids_166_205_untouched": all(not (166 <= int(finite_number(row.get("seed"), 0.0)) <= 205) for row in lattice_rows),
    }
    decision = (
        "candidate_space_gap_improved_continue_confidence_targets_v4"
        if candidate_space_improves_g58 and gates["measured_contexts_ge_60"] and gates["primary_1000_2000_stable_contexts_ge_40"]
        else "candidate_space_gap_expand_flow_shield_lattice"
        if math.isfinite(candidate_space_oracle_gap_vs_g58) and not candidate_space_improves_g58
        else "lattice_adapter_smoke_passed_server_required_for_full_run"
    )
    summary = {
        "schema_version": "phase5p5_repair5g510_lattice_counterfactual_analysis_summary_v1",
        "decision": decision,
        "counterfactuals_run": bool(lattice_rows),
        "measured_contexts": measured_contexts,
        "primary_1000_2000_stable_contexts": len(stable_rows),
        "complete_primary_contexts": complete_primary_contexts,
        "later_iteration_measured_contexts": later_iteration_contexts,
        "oracle_beats_static_fraction": len(beats_static) / len(finite_static) if finite_static else None,
        "mean_oracle_gap_over_static": as_jsonable(mean(finite_static)),
        "oracle_beats_additive_fraction": len(beats_additive) / len(finite_additive) if finite_additive else None,
        "mean_oracle_gap_over_additive": as_jsonable(mean(finite_additive)),
        "candidate_space_oracle_gap_vs_g58": as_jsonable(candidate_space_oracle_gap_vs_g58),
        "candidate_space_improves_g58": candidate_space_improves_g58,
        "best_single_candidate_train_only": best_single.get("candidate_id", ""),
        "per_candidate_win_distribution": dict(sorted(oracle_wins.items())),
        "per_map_agent_oracle_wins": {key: dict(counter) for key, counter in sorted(per_map_agent.items())},
        "no_solution_or_infeasible_probe_rows": no_solution_rows,
        "budget_sensitive_contexts": sum(1 for row in context_rows if row.get("label_class_hint") == "budget_sensitive_exclude"),
        "candidate_distribution_csv": str(resolve(args.candidate_table_csv, root)),
        "context_oracle_csv": str(resolve(args.context_table_csv, root)),
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Lattice Counterfactual Analysis\n\n"
        f"- decision: `{decision}`\n"
        f"- measured_contexts: `{measured_contexts}`\n"
        f"- primary_1000_2000_stable_contexts: `{len(stable_rows)}`\n"
        f"- oracle_beats_static_fraction: `{summary['oracle_beats_static_fraction']}`\n"
        f"- mean_oracle_gap_over_static: `{summary['mean_oracle_gap_over_static']}`\n"
        f"- oracle_beats_additive_fraction: `{summary['oracle_beats_additive_fraction']}`\n"
        f"- mean_oracle_gap_over_additive: `{summary['mean_oracle_gap_over_additive']}`\n"
        f"- candidate_space_oracle_gap_vs_g58: `{summary['candidate_space_oracle_gap_vs_g58']}`\n"
        f"- later_iteration_measured_contexts: `{later_iteration_contexts}`\n"
        f"- no_solution_or_infeasible_probe_rows: `{no_solution_rows}`\n\n"
        "Negative gaps mean the new lattice oracle is better. These are observed-ID-only diagnostic counterfactuals; "
        "they are not Phase5.5, Phase6, runtime-policy, or AAAI-ready evidence.\n",
    )
    print(json.dumps({"decision": decision, "measured_contexts": measured_contexts, "candidate_space_oracle_gap_vs_g58": summary["candidate_space_oracle_gap_vs_g58"]}))
    return 0 if bool(lattice_rows) and gates["observed_ids_only"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
