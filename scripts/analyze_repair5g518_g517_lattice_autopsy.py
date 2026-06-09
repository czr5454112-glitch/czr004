"""Autopsy the G5.17 targeted lattice before proposing G5.18 candidates."""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import (  # noqa: E402
    as_jsonable,
    best_candidate,
    candidate_scores_by_context_budget,
    mean,
    score_for_candidate,
    score_from_probe,
)
from repair5g518_common import (  # noqa: E402
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_MARGIN,
    G517_ADAPTER_SUMMARY,
    G517_ORACLE_CANDIDATE_TABLE,
    G517_ORACLE_CONTEXT_TABLE,
    G517_ORACLE_SUMMARY,
    G517_SMOKE_SUMMARY,
    G517_TARGETED_INTEGRITY_SUMMARY,
    G517_TARGETED_RESULTS,
    G518_AUTOPSY_REPORT,
    G518_AUTOPSY_SUMMARY,
    G518_CANDIDATE_DOMINANCE,
    G518_CLOSED_CLAIMS,
    G518_CONTEXT_FAMILY_WINNERS,
    candidate_params,
    family_for_candidate,
    finite_number,
    map_family,
    maybe_read_json,
    observed_id_flags,
    old14_candidate_ids,
    param_distance,
    plan_rows,
    read_csv_dicts,
    repair_candidate_ids,
    repo_root,
    resolve,
    selected_candidate_family_lookup,
    write_csv,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(G517_TARGETED_RESULTS))
    parser.add_argument("--probe-plan-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--error-bank-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g516_error_bank.csv"))
    parser.add_argument("--adapter-summary-json", type=Path, default=Path(G517_ADAPTER_SUMMARY))
    parser.add_argument("--smoke-summary-json", type=Path, default=Path(G517_SMOKE_SUMMARY))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G517_TARGETED_INTEGRITY_SUMMARY))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(G517_ORACLE_SUMMARY))
    parser.add_argument("--g517-context-oracle-csv", type=Path, default=Path(G517_ORACLE_CONTEXT_TABLE))
    parser.add_argument("--g517-candidate-distribution-csv", type=Path, default=Path(G517_ORACLE_CANDIDATE_TABLE))
    parser.add_argument("--dominance-csv", type=Path, default=Path(G518_CANDIDATE_DOMINANCE))
    parser.add_argument("--context-family-csv", type=Path, default=Path(G518_CONTEXT_FAMILY_WINNERS))
    parser.add_argument("--summary-json", type=Path, default=Path(G518_AUTOPSY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G518_AUTOPSY_REPORT))
    return parser.parse_args(argv)


def context_categories(plan: list[dict[str, Any]], error_bank: list[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for row in plan + error_bank:
        key = str(row.get("normalized_context_key", ""))
        category = str(row.get("error_category", ""))
        if key and category:
            out[key].add(category)
    return out


def rank_by_candidate(scores: dict[str, dict[str, Any]]) -> dict[str, int]:
    ranked = sorted(
        (
            (candidate, score_from_probe(row))
            for candidate, row in scores.items()
            if math.isfinite(score_from_probe(row))
        ),
        key=lambda item: (item[1], item[0]),
    )
    return {candidate: index + 1 for index, (candidate, _score) in enumerate(ranked)}


def nearest_old_candidate(candidate: str, old_ids: set[str]) -> tuple[str, float]:
    params = candidate_params(candidate)
    best = ("", math.inf)
    for old in old_ids:
        dist = param_distance(params, candidate_params(old))
        if dist < best[1]:
            best = (old, dist)
    return best


def verify_g517_artifacts(
    *,
    rows: list[dict[str, Any]],
    plan: list[dict[str, Any]],
    adapter: dict[str, Any],
    smoke: dict[str, Any],
    integrity: dict[str, Any],
    oracle: dict[str, Any],
) -> dict[str, Any]:
    candidate_ids = set(str(row.get("candidate_id", "")) for row in rows)
    contexts = set(str(row.get("normalized_context_key", "")) for row in rows)
    budgets = sorted({int(finite_number(row.get("short_budget_ms"), -1)) for row in rows})
    repair_ids = set(repair_candidate_ids())
    flags = observed_id_flags(rows + plan)
    gates = {
        "adapter_recognition_passed": adapter.get("decision") == "adapter_recognition_passed_continue_local_probe",
        "adapter_smoke_passed": smoke.get("decision") == "adapter_smoke_passed_continue_targeted_probe",
        "targeted_probe_integrity_passed": integrity.get("decision") == "targeted_probe_integrity_passed_continue_oracle",
        "targeted_oracle_no_gain": oracle.get("decision") == "targeted_repair_lattice_no_oracle_gain_continue_lattice_design",
        "rows_eq_960": len(rows) == 960,
        "contexts_eq_20": len(contexts) == 20,
        "candidates_eq_24": len(candidate_ids) == 24,
        "repair_candidates_eq_10": len(candidate_ids & repair_ids) == 10,
        "budgets_eq_1000_2000": budgets == [1000, 2000],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "observed_ids_only": flags["observed_ids_only"],
    }
    return {
        "gates": gates,
        "passed": all(gates.values()),
        "rows": len(rows),
        "contexts": len(contexts),
        "candidates": len(candidate_ids),
        "repair_candidates": len(candidate_ids & repair_ids),
        "budgets": budgets,
        **flags,
    }


def summarize_candidates(
    rows: list[dict[str, Any]],
    grouped: dict[tuple[str, float], dict[str, dict[str, Any]]],
    *,
    old_ids: set[str],
    repair_ids: set[str],
    oracle_wins: Counter[str],
) -> list[dict[str, Any]]:
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rank_values: dict[str, list[int]] = defaultdict(list)
    dominance: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        by_candidate[candidate].append(row)
    for (_key, _budget), scores in grouped.items():
        ranks = rank_by_candidate(scores)
        for candidate, rank in ranks.items():
            rank_values[candidate].append(rank)
        for candidate in repair_ids:
            nearest, _dist = nearest_old_candidate(candidate, old_ids)
            if candidate not in scores or nearest not in scores:
                continue
            candidate_score = score_for_candidate(scores, candidate)
            nearest_score = score_for_candidate(scores, nearest)
            if math.isfinite(candidate_score) and math.isfinite(nearest_score):
                if candidate_score > nearest_score + DEFAULT_MARGIN:
                    dominance[candidate]["worse_than_nearest_old"] += 1
                elif candidate_score < nearest_score - DEFAULT_MARGIN:
                    dominance[candidate]["better_than_nearest_old"] += 1
                else:
                    dominance[candidate]["tied_nearest_old"] += 1
    out: list[dict[str, Any]] = []
    for candidate in sorted(by_candidate):
        params = candidate_params(candidate)
        group = by_candidate[candidate]
        scores = [score_from_probe(row) for row in group]
        finite_scores = [value for value in scores if math.isfinite(value)]
        deltas = [finite_number(row.get("delta_vs_static_in_same_context"), math.nan) for row in group]
        finite_deltas = [value for value in deltas if math.isfinite(value)]
        helpful = [value for value in finite_deltas if value < -DEFAULT_MARGIN]
        harmful = [value for value in finite_deltas if value > DEFAULT_MARGIN]
        nearest, distance = nearest_old_candidate(candidate, old_ids) if candidate in repair_ids else ("", math.inf)
        ranks = rank_values.get(candidate, [])
        worse = dominance[candidate]["worse_than_nearest_old"]
        better = dominance[candidate]["better_than_nearest_old"]
        tied = dominance[candidate]["tied_nearest_old"]
        dominated = candidate in repair_ids and better == 0 and worse > 0
        if candidate in repair_ids and dominated:
            failure_mode = "dominated_by_nearest_old"
        elif candidate in repair_ids and len(harmful) > len(helpful):
            failure_mode = "harmful_more_than_helpful"
        elif candidate in repair_ids and oracle_wins.get(candidate, 0) == 0:
            failure_mode = "no_oracle_wins"
        else:
            failure_mode = "control_or_winner"
        row = {
            "candidate_id": candidate,
            "candidate_family": family_for_candidate(candidate, params),
            "is_old14_control": candidate in old_ids,
            "is_repair5g516_candidate": candidate in repair_ids,
            "rows": len(group),
            "finite_rows": len(finite_scores),
            "infeasible_or_no_solution_rows": len(group) - len(finite_scores),
            "oracle_win_count": oracle_wins.get(candidate, 0),
            "mean_score": as_jsonable(mean(finite_scores)),
            "mean_delta_vs_static": as_jsonable(mean(finite_deltas)),
            "min_delta_vs_static": as_jsonable(min(finite_deltas) if finite_deltas else math.inf),
            "max_delta_vs_static": as_jsonable(max(finite_deltas) if finite_deltas else math.inf),
            "helpful_vs_static_count": len(helpful),
            "harmful_vs_static_count": len(harmful),
            "mean_rank": as_jsonable(mean(float(value) for value in ranks)),
            "rank_le_3_count": sum(1 for value in ranks if value <= 3),
            "nearest_old_candidate": nearest,
            "nearest_old_param_distance": as_jsonable(distance),
            "better_than_nearest_old_rows": better,
            "tied_nearest_old_rows": tied,
            "worse_than_nearest_old_rows": worse,
            "dominated_by_nearest_old": dominated,
            "failure_mode": failure_mode,
        }
        if params is not None:
            row.update(params.as_feature_dict())
        out.append(row)
    return out


def direction_autopsy(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    directions = {
        "lower_beta": lambda row: finite_number(row.get("flow_shield_beta"), math.inf) <= 0.25,
        "lower_cap": lambda row: finite_number(row.get("max_flow_shield"), math.inf) <= 0.50,
        "faster_congestion_decay": lambda row: finite_number(row.get("rho_cong"), math.inf) <= 0.92,
        "faster_flow_decay": lambda row: finite_number(row.get("rho_flow"), math.inf) <= 0.95,
        "static_boundary_or_c_only": lambda row: bool(row.get("c_only")) or "static_boundary" in str(row.get("candidate_family", "")),
    }
    out = []
    repair_rows = [row for row in candidate_rows if str(row.get("is_repair5g516_candidate", "")).lower() == "true" or row.get("is_repair5g516_candidate") is True]
    for name, predicate in directions.items():
        members = [row for row in repair_rows if predicate(row)]
        out.append(
            {
                "direction": name,
                "candidate_count": len(members),
                "oracle_win_count": sum(int(finite_number(row.get("oracle_win_count"), 0.0)) for row in members),
                "helpful_vs_static_count": sum(int(finite_number(row.get("helpful_vs_static_count"), 0.0)) for row in members),
                "harmful_vs_static_count": sum(int(finite_number(row.get("harmful_vs_static_count"), 0.0)) for row in members),
                "mean_delta_vs_static": as_jsonable(mean(finite_number(row.get("mean_delta_vs_static"), math.nan) for row in members)),
                "interpretation": "falsified_or_weak" if members else "not_tested",
            }
        )
    return out


def context_family_rows(
    context_oracle_rows: list[dict[str, Any]],
    categories: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], Counter[str], Counter[str]]:
    rows = []
    family_counts: Counter[str] = Counter()
    map_family_counts: Counter[str] = Counter()
    for row in context_oracle_rows:
        key = str(row.get("normalized_context_key", ""))
        old_winner = str(row.get("old14_oracle_candidate", ""))
        family = family_for_candidate(old_winner, candidate_params(old_winner))
        map_name = str(row.get("normalized_context_key", "")).split("|", 1)[0]
        mf = map_family(map_name)
        family_counts[family] += 1
        map_family_counts[mf] += 1
        rows.append(
            {
                "normalized_context_key": key,
                "short_budget_ms": row.get("short_budget_ms", ""),
                "map_family": mf,
                "error_categories": ";".join(sorted(categories.get(key, set()))),
                "old14_oracle_candidate": old_winner,
                "old14_oracle_family": family,
                "new24_oracle_candidate": row.get("new24_oracle_candidate", ""),
                "new24_oracle_is_repair_candidate": row.get("new24_oracle_is_repair_candidate", ""),
                "new_oracle_gap_vs_old_oracle": row.get("new_oracle_gap_vs_old_oracle", ""),
                "new_oracle_gap_vs_static": row.get("new_oracle_gap_vs_static", ""),
                "new_oracle_gap_vs_additive": row.get("new_oracle_gap_vs_additive", ""),
            }
        )
    return rows, family_counts, map_family_counts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_dicts(resolve(args.results_csv, root))
    plan = plan_rows(resolve(args.probe_plan_csv, root))
    error_bank = read_csv_dicts(resolve(args.error_bank_csv, root))
    adapter = maybe_read_json(args.adapter_summary_json)
    smoke = maybe_read_json(args.smoke_summary_json)
    integrity = maybe_read_json(args.integrity_summary_json)
    oracle = maybe_read_json(args.oracle_summary_json)
    g517_context_oracle = read_csv_dicts(resolve(args.g517_context_oracle_csv, root))

    artifact_check = verify_g517_artifacts(
        rows=rows,
        plan=plan,
        adapter=adapter,
        smoke=smoke,
        integrity=integrity,
        oracle=oracle,
    )
    if not artifact_check["passed"]:
        summary = {
            "schema_version": "phase5p5_repair5g518_g517_lattice_autopsy_summary_v1",
            "decision": "g517_artifacts_missing_or_invalid_stop",
            "artifact_check": artifact_check,
            **G518_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        write_text_file(args.report, "# Phase5.5 Repair5G.5.18 G5.17 Lattice Autopsy\n\n- decision: `g517_artifacts_missing_or_invalid_stop`\n")
        print({"decision": summary["decision"], "artifact_check": artifact_check})
        return 2

    old_ids = set(old14_candidate_ids(root))
    repair_ids = set(repair_candidate_ids())
    all_ids = old_ids | repair_ids
    grouped = candidate_scores_by_context_budget(rows, allowed_candidates=all_ids)
    oracle_wins: Counter[str] = Counter()
    for (_key, _budget), scores in grouped.items():
        winner, _score = best_candidate(scores)
        if winner:
            oracle_wins[winner] += 1
    candidate_rows = summarize_candidates(rows, grouped, old_ids=old_ids, repair_ids=repair_ids, oracle_wins=oracle_wins)
    categories = context_categories(plan, error_bank)
    context_rows, winner_families, map_families = context_family_rows(g517_context_oracle, categories)
    direction_rows = direction_autopsy(candidate_rows)
    write_csv(args.dominance_csv, candidate_rows)
    write_csv(args.context_family_csv, context_rows)

    repair_rows = [row for row in candidate_rows if row["is_repair5g516_candidate"]]
    old_rows = [row for row in candidate_rows if row["is_old14_control"]]
    dominated_repair = [row for row in repair_rows if row["dominated_by_nearest_old"]]
    summary = {
        "schema_version": "phase5p5_repair5g518_g517_lattice_autopsy_summary_v1",
        "decision": "g517_lattice_autopsy_passed_continue_surrogate_proposal",
        "artifact_check": artifact_check,
        "old_candidate_count": len(old_ids),
        "repair_candidate_count": len(repair_ids),
        "context_budget_pairs": len(grouped),
        "old_winner_family_distribution": dict(sorted(winner_families.items())),
        "map_family_distribution": dict(sorted(map_families.items())),
        "repair_candidate_oracle_win_count": sum(int(row["oracle_win_count"]) for row in repair_rows),
        "repair_candidates_dominated_by_nearest_old": len(dominated_repair),
        "repair_mean_delta_vs_static": as_jsonable(mean(finite_number(row.get("mean_delta_vs_static"), math.nan) for row in repair_rows)),
        "old_mean_delta_vs_static": as_jsonable(mean(finite_number(row.get("mean_delta_vs_static"), math.nan) for row in old_rows)),
        "direction_autopsy": direction_rows,
        "candidate_dominance_csv": str(resolve(args.dominance_csv, root)),
        "context_family_winners_csv": str(resolve(args.context_family_csv, root)),
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    direction_lines = "\n".join(
        f"- `{row['direction']}`: candidates `{row['candidate_count']}`, oracle wins `{row['oracle_win_count']}`, mean delta `{row['mean_delta_vs_static']}`"
        for row in direction_rows
    )
    top_old = sorted(old_rows, key=lambda row: (-int(row["oracle_win_count"]), finite_number(row.get("mean_delta_vs_static"), math.inf)))[:8]
    top_old_lines = "\n".join(
        f"- `{row['candidate_id']}` ({row['candidate_family']}): wins `{row['oracle_win_count']}`, mean_delta `{row['mean_delta_vs_static']}`"
        for row in top_old
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.18 G5.17 Lattice Autopsy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- rows: `{artifact_check['rows']}`\n"
        f"- context_budget_pairs: `{len(grouped)}`\n"
        f"- old_candidate_count: `{len(old_ids)}`\n"
        f"- repair_candidate_count: `{len(repair_ids)}`\n"
        f"- repair_candidate_oracle_win_count: `{summary['repair_candidate_oracle_win_count']}`\n"
        f"- repair_candidates_dominated_by_nearest_old: `{len(dominated_repair)}`\n"
        f"- old_winner_family_distribution: `{summary['old_winner_family_distribution']}`\n\n"
        "## Strong Old Neighborhoods\n\n"
        f"{top_old_lines}\n\n"
        "## Parameter Direction Autopsy\n\n"
        f"{direction_lines}\n\n"
        "The G5.17 adapter/probe path is valid, but the conservative G5.16 repair candidates remain weak or dominated. G5.18 should expand around block-heavy, wait, high-beta, low-beta-high-cap, and flow-decay neighborhoods instead of only lowering beta/cap.\n",
    )
    print({"decision": summary["decision"], "repair_candidate_oracle_win_count": summary["repair_candidate_oracle_win_count"]})
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
