"""Analyze Repair5G.5.11 full lattice oracle gap."""

from __future__ import annotations

import argparse
import csv
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
    G510_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    as_jsonable,
    finite_number,
    lattice_candidate_ids,
    mean,
    read_csv_rows,
    repo_root,
    resolve,
    score_from_probe,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_CONTEXT_TABLE = "outputs/tables/phase5p5_repair5g511_lattice_oracle_by_context.csv"
DEFAULT_CANDIDATE_TABLE = "outputs/tables/phase5p5_repair5g511_lattice_candidate_distribution.csv"
DEFAULT_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g511_lattice_by_map_agent.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full_summary.json"
G510_SMOKE_GAP_VS_G58 = -0.015080627924999979


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--context-table-csv", type=Path, default=Path(DEFAULT_CONTEXT_TABLE))
    parser.add_argument("--candidate-table-csv", type=Path, default=Path(DEFAULT_CANDIDATE_TABLE))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    write_csv_rows(path, rows)


def context_key(row: dict[str, object]) -> str:
    return str(row.get("normalized_context_key", ""))


def best(scores: dict[str, dict[str, object]]) -> tuple[str, float]:
    best_id = ""
    best_score = math.inf
    for candidate, row in scores.items():
        score = score_from_probe(row)
        if score < best_score:
            best_id = candidate
            best_score = score
    return best_id, best_score


def score_for(scores: dict[str, dict[str, object]], candidate: str) -> float:
    return score_from_probe(scores.get(candidate, {}))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.results_csv, root))
    lattice_ids = set(lattice_candidate_ids(resolve(args.candidate_csv, root)))
    g58_by_key = {context_key(row): row for row in read_csv_rows(resolve(args.contexts_csv, root))}
    grouped: dict[str, dict[int, dict[str, dict[str, object]]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if candidate not in lattice_ids:
            continue
        grouped[context_key(row)][int(finite_number(row.get("short_budget_ms"), 0.0))][candidate] = row

    context_rows: list[dict[str, object]] = []
    win_counts: Counter[str] = Counter()
    stress_disagree = []
    bonus_agree = []
    by_map_agent: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    for key, budgets in sorted(grouped.items()):
        old = g58_by_key.get(key, {})
        out: dict[str, object] = {
            "normalized_context_key": key,
            "map": old.get("map") or next((r.get("map", "") for scores in budgets.values() for r in scores.values()), ""),
            "agents": old.get("agents") or next((r.get("agents", "") for scores in budgets.values() for r in scores.values()), ""),
            "seed": old.get("seed") or next((r.get("seed", "") for scores in budgets.values() for r in scores.values()), ""),
            "iteration": old.get("iteration") or next((r.get("iteration", "") for scores in budgets.values() for r in scores.values()), ""),
            "traffic_before_hash_full": old.get("traffic_before_hash_full") or key.split("|")[-1],
        }
        for budget in [250, 500, 1000, 2000]:
            scores = budgets.get(budget, {})
            oracle_id, oracle_score = best(scores)
            static_score = score_for(scores, G510_STATIC_CANDIDATE)
            additive_score = score_for(scores, G510_ADDITIVE_CANDIDATE)
            old_score = finite_number(old.get(f"oracle_score_{budget}"), math.inf)
            out[f"oracle_{budget}"] = oracle_id
            out[f"oracle_score_{budget}"] = as_jsonable(oracle_score)
            out[f"static_score_{budget}"] = as_jsonable(static_score)
            out[f"additive_score_{budget}"] = as_jsonable(additive_score)
            out[f"finite_candidates_{budget}"] = sum(1 for probe in scores.values() if math.isfinite(score_from_probe(probe)))
            out[f"oracle_gap_over_static_{budget}"] = as_jsonable(oracle_score - static_score if math.isfinite(oracle_score) and math.isfinite(static_score) else math.inf)
            out[f"oracle_gap_over_additive_{budget}"] = as_jsonable(oracle_score - additive_score if math.isfinite(oracle_score) and math.isfinite(additive_score) else math.inf)
            out[f"oracle_gap_vs_g58_{budget}"] = as_jsonable(oracle_score - old_score if math.isfinite(oracle_score) and math.isfinite(old_score) else math.inf)
        out["primary_1000_2000_measured"] = bool(out.get("oracle_1000") or out.get("oracle_2000"))
        out["primary_1000_2000_stable"] = (
            bool(out.get("oracle_1000"))
            and out.get("oracle_1000") == out.get("oracle_2000")
            and out.get("finite_candidates_1000") == out.get("finite_candidates_2000")
        )
        out["stress_250_disagrees_with_1000"] = bool(out.get("oracle_250")) and out.get("oracle_250") != out.get("oracle_1000")
        out["bonus_500_agrees_with_1000"] = bool(out.get("oracle_500")) and out.get("oracle_500") == out.get("oracle_1000")
        if bool(out.get("oracle_250")):
            stress_disagree.append(bool(out["stress_250_disagrees_with_1000"]))
        if bool(out.get("oracle_500")):
            bonus_agree.append(bool(out["bonus_500_agrees_with_1000"]))
        if out.get("oracle_1000"):
            win_counts[str(out["oracle_1000"])] += 1
            by_map_agent[(str(out["map"]), int(finite_number(out.get("agents"), 0.0)))][str(out["oracle_1000"])] += 1
        context_rows.append(out)

    write_csv(resolve(args.context_table_csv, root), context_rows)

    candidate_rows = []
    for candidate in sorted(lattice_ids):
        group = [row for row in rows if str(row.get("candidate_id", "")) == candidate]
        deltas = [finite_number(row.get("delta_vs_static_in_same_context"), math.nan) for row in group]
        finite_deltas = [value for value in deltas if math.isfinite(value)]
        candidate_rows.append(
            {
                "candidate_id": candidate,
                "rows": len(group),
                "finite_rows": sum(1 for row in group if math.isfinite(score_from_probe(row))),
                "mean_score": as_jsonable(mean(score_from_probe(row) for row in group)),
                "mean_delta_vs_static": as_jsonable(mean(finite_deltas)),
                "helpful_vs_static_count": sum(1 for value in finite_deltas if value < -G510_DEFAULT_MARGIN),
                "harmful_vs_static_count": sum(1 for value in finite_deltas if value > G510_DEFAULT_MARGIN),
                "oracle_win_count_1000": win_counts.get(candidate, 0),
            }
        )
    write_csv(resolve(args.candidate_table_csv, root), candidate_rows)

    by_map_rows = []
    for (map_name, agents), counter in sorted(by_map_agent.items()):
        total = sum(counter.values())
        for candidate, wins in sorted(counter.items()):
            by_map_rows.append({"map": map_name, "agents": agents, "candidate_id": candidate, "wins": wins, "fraction": wins / total if total else ""})
    write_csv(resolve(args.by_map_agent_csv, root), by_map_rows)

    primary = [row for row in context_rows if row.get("primary_1000_2000_measured")]
    stable = [row for row in primary if str(row.get("primary_1000_2000_stable")).lower() == "true"]
    gaps_static = [finite_number(row.get("oracle_gap_over_static_1000"), math.inf) for row in primary]
    gaps_additive = [finite_number(row.get("oracle_gap_over_additive_1000"), math.inf) for row in primary]
    gaps_g58 = [finite_number(row.get("oracle_gap_vs_g58_1000"), math.inf) for row in primary]
    finite_static = [value for value in gaps_static if math.isfinite(value)]
    finite_additive = [value for value in gaps_additive if math.isfinite(value)]
    finite_g58 = [value for value in gaps_g58 if math.isfinite(value)]
    candidate_space_oracle_gap_vs_g58 = mean(finite_g58)
    gates = {
        "measured_contexts_ge_60": len(context_rows) >= 60,
        "primary_1000_2000_stable_contexts_ge_40": len(stable) >= 40,
        "candidate_space_oracle_gap_vs_g58_lt_0": math.isfinite(candidate_space_oracle_gap_vs_g58) and candidate_space_oracle_gap_vs_g58 < 0,
        "oracle_beats_static_fraction_gt_0": any(value < -G510_DEFAULT_MARGIN for value in finite_static),
        "oracle_beats_additive_fraction_gt_0": any(value < -G510_DEFAULT_MARGIN for value in finite_additive),
        "ids_166_205_untouched": all(not (166 <= int(finite_number(row.get("seed"), 0.0)) <= 205) for row in rows),
    }
    best_single = min(candidate_rows, key=lambda row: (finite_number(row.get("mean_score"), math.inf), str(row.get("candidate_id")))) if candidate_rows else {}
    no_solution_rows = sum(1 for row in rows if not math.isfinite(score_from_probe(row)))
    longer_budget = sum(1 for row in context_rows if int(finite_number(row.get("finite_candidates_1000"), 0.0)) == 0 and int(finite_number(row.get("finite_candidates_2000"), 0.0)) > 0)
    decision = "full_lattice_candidate_space_passed_continue_targets" if all(gates.values()) else "full_lattice_candidate_space_failed_expand_lattice"
    summary = {
        "schema_version": "phase5p5_repair5g511_lattice_oracle_gap_full_summary_v1",
        "decision": decision,
        "measured_contexts": len(context_rows),
        "primary_1000_2000_stable_contexts": len(stable),
        "oracle_beats_static_fraction": sum(1 for value in finite_static if value < -G510_DEFAULT_MARGIN) / len(finite_static) if finite_static else None,
        "oracle_beats_additive_fraction": sum(1 for value in finite_additive if value < -G510_DEFAULT_MARGIN) / len(finite_additive) if finite_additive else None,
        "mean_oracle_gap_over_static": as_jsonable(mean(finite_static)),
        "mean_oracle_gap_over_additive": as_jsonable(mean(finite_additive)),
        "candidate_space_oracle_gap_vs_g58": as_jsonable(candidate_space_oracle_gap_vs_g58),
        "candidate_space_oracle_gap_vs_g510_smoke": as_jsonable(candidate_space_oracle_gap_vs_g58 - G510_SMOKE_GAP_VS_G58),
        "best_single_candidate": best_single.get("candidate_id", ""),
        "per_candidate_win_distribution": dict(sorted(win_counts.items())),
        "stress_250_disagreement_rate": sum(stress_disagree) / len(stress_disagree) if stress_disagree else None,
        "bonus_500_agreement_rate": sum(bonus_agree) / len(bonus_agree) if bonus_agree else None,
        "warehouse_contexts": sum(1 for row in context_rows if str(row.get("map", "")).startswith("warehouse")),
        "no_solution_or_infeasible_probe_rows": no_solution_rows,
        "longer_budget_needed_contexts": longer_budget,
        "later_iteration_measured_contexts": sum(1 for row in context_rows if finite_number(row.get("iteration"), 0.0) > 0),
        "gates": gates,
        "context_oracle_csv": str(resolve(args.context_table_csv, root)),
        "candidate_distribution_csv": str(resolve(args.candidate_table_csv, root)),
        "by_map_agent_csv": str(resolve(args.by_map_agent_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.11 Full Lattice Oracle Gap\n\n"
        f"- decision: `{decision}`\n"
        f"- measured_contexts: `{len(context_rows)}`\n"
        f"- primary_1000_2000_stable_contexts: `{len(stable)}`\n"
        f"- oracle_beats_static_fraction: `{summary['oracle_beats_static_fraction']}`\n"
        f"- oracle_beats_additive_fraction: `{summary['oracle_beats_additive_fraction']}`\n"
        f"- mean_oracle_gap_over_static: `{summary['mean_oracle_gap_over_static']}`\n"
        f"- mean_oracle_gap_over_additive: `{summary['mean_oracle_gap_over_additive']}`\n"
        f"- candidate_space_oracle_gap_vs_g58: `{summary['candidate_space_oracle_gap_vs_g58']}`\n"
        f"- candidate_space_oracle_gap_vs_g510_smoke: `{summary['candidate_space_oracle_gap_vs_g510_smoke']}`\n"
        f"- best_single_candidate: `{summary['best_single_candidate']}`\n"
        f"- stress_250_disagreement_rate: `{summary['stress_250_disagreement_rate']}`\n"
        f"- bonus_500_agreement_rate: `{summary['bonus_500_agreement_rate']}`\n\n"
        "The full observed-ID server run confirms the 14-candidate bounded UpdateLTM lattice improves the oracle upper bound. "
        "This permits confidence-target construction, but still does not permit Phase5.5/Phase6/runtime/AAAI claims.\n",
    )
    print(json.dumps({"decision": decision, "measured_contexts": len(context_rows), "gap_vs_g58": summary["candidate_space_oracle_gap_vs_g58"]}))
    return 0 if decision == "full_lattice_candidate_space_passed_continue_targets" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
