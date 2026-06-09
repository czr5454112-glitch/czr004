"""Run G5.21 full-primary confirmation only if the targeted gate passes."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g510_common import read_jsonl  # noqa: E402
from repair5g521_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G521_CLOSED_CLAIMS,
    G521_FULL_CANDIDATE_DISTRIBUTION_CSV,
    G521_FULL_INTEGRITY_REPORT,
    G521_FULL_INTEGRITY_SUMMARY,
    G521_FULL_LOG_DIR,
    G521_FULL_ORACLE_BY_CONTEXT_CSV,
    G521_FULL_ORACLE_REPORT,
    G521_FULL_ORACLE_SUMMARY,
    G521_FULL_RESULTS_CSV,
    G521_FULL_SCENARIO_DIR,
    G521_FULL_SCENARIO_METADATA,
    G521_FULL_SELECTED_CSV,
    G521_TARGETED_CANDIDATE_DISTRIBUTION_CSV,
    G521_TARGETED_ORACLE_SUMMARY,
    PRIMARY_BUDGETS,
    STATIC_FLOW_SHIELD_CANDIDATE,
    all_contexts_from_targets,
    best_row,
    boolish,
    candidate_recognition_counts,
    candidate_role,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    family_for_candidate,
    finite_delta,
    finite_number,
    g518_retained_candidate_ids,
    mean,
    observed_id_flags,
    observed_id_guard,
    old14_candidate_ids,
    read_json_file,
    read_rows,
    repo_root,
    row_finite_solution,
    rows_by_context_budget,
    score,
    selected_g521_candidate_ids,
    write_json_file,
    write_probe_csv_from_jsonl,
    write_rows,
    write_text_file,
    csv_number,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(G521_FULL_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(G521_FULL_SCENARIO_METADATA))
    parser.add_argument("--results-csv", type=Path, default=Path(G521_FULL_RESULTS_CSV))
    parser.add_argument("--selected-csv", type=Path, default=Path(G521_FULL_SELECTED_CSV))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G521_FULL_INTEGRITY_SUMMARY))
    parser.add_argument("--integrity-report", type=Path, default=Path(G521_FULL_INTEGRITY_REPORT))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(G521_FULL_ORACLE_SUMMARY))
    parser.add_argument("--oracle-report", type=Path, default=Path(G521_FULL_ORACLE_REPORT))
    parser.add_argument("--oracle-by-context-csv", type=Path, default=Path(G521_FULL_ORACLE_BY_CONTEXT_CSV))
    parser.add_argument("--candidate-distribution-csv", type=Path, default=Path(G521_FULL_CANDIDATE_DISTRIBUTION_CSV))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def write_skip(args: argparse.Namespace, reason: str, targeted_decision: str) -> None:
    integrity = {
        "schema_version": "phase5p5_repair5g521_full_primary_confirmation_integrity_summary_v1",
        "decision": "full_primary_confirmation_skipped_targeted_gate_failed",
        "probe_ran": False,
        "no_run_reason": reason,
        "targeted_decision": targeted_decision,
        **G521_CLOSED_CLAIMS,
    }
    oracle = {
        "schema_version": "phase5p5_repair5g521_full_primary_confirmation_oracle_summary_v1",
        "decision": "full_primary_confirmation_skipped_targeted_gate_failed",
        "oracle_analyzed": False,
        "no_run_reason": reason,
        "targeted_decision": targeted_decision,
        **G521_CLOSED_CLAIMS,
    }
    write_json_file(args.integrity_summary_json, integrity)
    write_json_file(args.oracle_summary_json, oracle)
    write_text_file(args.integrity_report, f"# Repair5G.5.21 Full-Primary Confirmation Integrity\n\n- decision: `{integrity['decision']}`\n- reason: `{reason}`\n")
    write_text_file(args.oracle_report, f"# Repair5G.5.21 Full-Primary Confirmation Oracle\n\n- decision: `{oracle['decision']}`\n- reason: `{reason}`\n")


def top_second_wave_candidates(limit: int = 8) -> list[str]:
    rows = read_rows(G521_TARGETED_CANDIDATE_DISTRIBUTION_CSV)
    ranked = [
        row
        for row in rows
        if str(row.get("candidate_role", "")) == "g521_second_wave"
    ]
    ranked = sorted(
        ranked,
        key=lambda row: (
            -int(finite_number(row.get("oracle_win_count"), 0)),
            int(finite_number(row.get("candidate_induced_no_solution_count"), 999)),
            finite_number(row.get("mean_score"), math.inf),
            str(row.get("candidate_id", "")),
        ),
    )
    out = [str(row.get("candidate_id", "")) for row in ranked[:limit] if str(row.get("candidate_id", ""))]
    if len(out) < limit:
        for candidate in selected_g521_candidate_ids():
            if candidate not in out:
                out.append(candidate)
            if len(out) >= limit:
                break
    return out[:limit]


def method_spec_for_budget(*, budget: int, selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, candidates: list[str]) -> MethodSpec:
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"repair5g521_full_primary_budget_{budget}ms_static_context",
        (
            "--repair5g5-selector-spec",
            str(selector_spec),
            "--repair5g-export-update-checkpoints-jsonl",
            str(checkpoint_jsonl),
            "--repair5g-checkpoint-topk-edges",
            "64",
            "--repair5g-checkpoint-edge-filter",
            "nonzero",
            "--repair5g-counterfactual-update-probe-jsonl",
            str(probe_jsonl),
            "--repair5g-counterfactual-candidates",
            ",".join(candidates),
            "--repair5g-counterfactual-short-budget-ms",
            str(int(budget)),
            "--repair5g-counterfactual-max-contexts",
            "1",
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )


def best_of(rows: list[dict[str, Any]], allowed: set[str]) -> dict[str, Any] | None:
    return best_row([row for row in rows if str(row.get("candidate_id", "")) in allowed])


def summarize_oracle(rows: list[dict[str, Any]], old_ids: set[str], g518_ids: set[str], g521_ids: set[str]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    old_plus_g518 = old_ids | g518_ids
    full = old_plus_g518 | g521_ids
    oracle_rows = []
    gaps_old_to_g518 = []
    gaps_g518_to_g521 = []
    deltas_static = []
    deltas_additive = []
    second_wave_contexts: set[str] = set()
    safe_second_wave_contexts: set[str] = set()
    second_wave_pairs = 0
    candidate_induced = 0
    recovery = 0
    annotated = []
    for (context, budget), group in sorted(rows_by_context_budget(rows).items()):
        static = best_of(group, {STATIC_FLOW_SHIELD_CANDIDATE})
        additive = best_of(group, {ADDITIVE_CANDIDATE})
        old14 = best_of(group, old_ids)
        old_g518 = best_of(group, old_plus_g518)
        full_best = best_of(group, full)
        static_finite = row_finite_solution(static)
        for row in group:
            candidate = str(row.get("candidate_id", ""))
            induced = static_finite and not row_finite_solution(row)
            recovers = (not static_finite) and row_finite_solution(row)
            if candidate in g521_ids and induced:
                candidate_induced += 1
            if candidate in g521_ids and recovers:
                recovery += 1
            annotated.append({**row, "_candidate_induced_failure": induced, "_candidate_recovers_static_failure": recovers})
        if row_finite_solution(old_g518) and row_finite_solution(old14):
            gaps_old_to_g518.append(score(old_g518) - score(old14))
        if row_finite_solution(full_best) and row_finite_solution(old_g518):
            gaps_g518_to_g521.append(score(full_best) - score(old_g518))
        if row_finite_solution(full_best) and row_finite_solution(static):
            deltas_static.append(score(full_best) - score(static))
        if row_finite_solution(full_best) and row_finite_solution(additive):
            deltas_additive.append(score(full_best) - score(additive))
        full_id = str((full_best or {}).get("candidate_id", ""))
        is_g521 = full_id in g521_ids
        safe = is_g521 and not (static_finite and not row_finite_solution(full_best))
        if is_g521:
            second_wave_pairs += 1
            second_wave_contexts.add(context)
            if safe:
                safe_second_wave_contexts.add(context)
        oracle_rows.append(
            {
                "normalized_context_key": context,
                "short_budget_ms": budget,
                "old14_oracle_candidate": (old14 or {}).get("candidate_id", ""),
                "old14_oracle_score": csv_number(score(old14)),
                "old14_plus_g518_oracle_candidate": (old_g518 or {}).get("candidate_id", ""),
                "old14_plus_g518_oracle_score": csv_number(score(old_g518)),
                "g521_full_oracle_candidate": full_id,
                "g521_full_oracle_score": csv_number(score(full_best)),
                "second_wave_oracle_winner": is_g521,
                "safe_second_wave_oracle_winner": safe,
                "gap_old14_to_g51822": csv_number(score(old_g518) - score(old14) if row_finite_solution(old_g518) and row_finite_solution(old14) else math.inf),
                "gap_g51822_to_g52130": csv_number(score(full_best) - score(old_g518) if row_finite_solution(full_best) and row_finite_solution(old_g518) else math.inf),
                **G521_CLOSED_CLAIMS,
            }
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in annotated:
        grouped[str(row.get("candidate_id", ""))].append(row)
    distribution = []
    for candidate, group in sorted(grouped.items()):
        wins = sum(
            1
            for oracle in oracle_rows
            if oracle["g521_full_oracle_candidate"] == candidate
        )
        finite_rows = [row for row in group if row_finite_solution(row)]
        distribution.append(
            {
                "candidate_id": candidate,
                "candidate_role": candidate_role(candidate, old_ids, g518_ids, g521_ids),
                "candidate_family": family_for_candidate(candidate),
                "rows": len(group),
                "finite_rows": len(finite_rows),
                "oracle_win_count": wins,
                "candidate_induced_no_solution_count": sum(1 for row in group if boolish(row.get("_candidate_induced_failure"))),
                "static_failure_candidate_recovers_count": sum(1 for row in group if boolish(row.get("_candidate_recovers_static_failure"))),
                "mean_score": csv_number(mean([score(row) for row in finite_rows])),
                **G521_CLOSED_CLAIMS,
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g521_full_primary_confirmation_oracle_summary_v1",
        "decision": "full_primary_confirmation_oracle_analyzed",
        "oracle_analyzed": True,
        "context_budget_pairs": len(oracle_rows),
        "old14_vs_g51822_oracle_gap": mean(gaps_old_to_g518),
        "g51822_vs_g52130_oracle_gap": mean(gaps_g518_to_g521),
        "second_wave_win_contexts": len(second_wave_contexts),
        "second_wave_win_budget_pairs": second_wave_pairs,
        "second_wave_safe_win_contexts": len(safe_second_wave_contexts),
        "mean_delta_vs_static": mean(deltas_static),
        "mean_delta_vs_additive": mean(deltas_additive),
        "candidate_induced_no_solution_delta": candidate_induced,
        "no_solution_recovery_delta": recovery,
        **G521_CLOSED_CLAIMS,
    }
    return summary, oracle_rows, distribution


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    targeted = read_json_file(G521_TARGETED_ORACLE_SUMMARY)
    if not boolish(targeted.get("targeted_gate_passed")):
        write_skip(args, "targeted second-wave gate did not pass", str(targeted.get("decision", "")))
        print(json.dumps({"decision": "full_primary_confirmation_skipped_targeted_gate_failed", "probe_ran": False}))
        return 0
    if int(args.max_workers) != 1:
        write_skip(args, "max_workers must be 1 for full-primary confirmation", str(targeted.get("decision", "")))
        return 2
    contexts = all_contexts_from_targets()
    observed_id_guard([row.get("seed", "") for row in contexts], label="G5.21 full-primary contexts")
    old_controls = old14_candidate_ids(root)
    retained_g518 = g518_retained_candidate_ids(limit=8)
    selected_g521 = top_second_wave_candidates(limit=8)
    candidates = old_controls + retained_g518 + selected_g521
    selected_rows = [
        {"candidate_id": candidate, "candidate_role": candidate_role(candidate, set(old_controls), set(retained_g518), set(selected_g521)), "selection_rule": "old14_or_retained8_or_targeted_top8"}
        for candidate in candidates
    ]
    write_rows(args.selected_csv, selected_rows)
    log_dir = resolve(G521_FULL_LOG_DIR, root)
    output_jsonl = log_dir / "phase5p5_repair5g521_full_primary_confirmation_runs.jsonl"
    command_log = log_dir / "phase5p5_repair5g521_full_primary_confirmation_commands.jsonl"
    update_log = log_dir / "phase5p5_repair5g521_full_primary_confirmation_ltm_updates.jsonl"
    probe_jsonl = log_dir / "phase5p5_repair5g521_full_primary_confirmation_update_probes.jsonl"
    checkpoint_jsonl = log_dir / "phase5p5_repair5g521_full_primary_confirmation_checkpoints.jsonl"
    results_csv = resolve(args.results_csv, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, results_csv]:
            path.unlink(missing_ok=True)
    temp_dir = log_dir / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=resolve(args.scenario_dir, root),
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=sorted({str(row["map"]) for row in contexts}),
        agent_counts=sorted({int(float(row["agents"])) for row in contexts}),
        instance_ids=sorted({int(float(row["seed"])) for row in contexts}),
    )
    for combo in contexts:
        for budget in PRIMARY_BUDGETS:
            spec = method_spec_for_budget(
                budget=int(budget),
                selector_spec=resolve(args.selector_spec_json, root),
                probe_jsonl=probe_jsonl,
                checkpoint_jsonl=checkpoint_jsonl,
                candidates=candidates,
            )
            solver_rows, _updates, command_row = run_one_solver_task(
                root=root,
                binary=resolve(args.binary, root),
                scenario_dir=resolve(args.scenario_dir, root),
                temp_dir=temp_dir,
                update_log=update_log,
                map_name=str(combo["map"]),
                agents=int(float(combo["agents"])),
                seed=int(float(combo["seed"])),
                time_limit_sec=float(args.time_limit_sec),
                ltm_max_iterations=int(args.ltm_max_iterations),
                spec=spec,
                manifest="phase5p5-repair5g521-full-primary-confirmation",
            )
            for row in solver_rows:
                append_jsonl(output_jsonl, row)
            append_jsonl(command_log, command_row)
    write_probe_csv_from_jsonl(probe_jsonl, results_csv)
    result_rows = read_rows(results_csv)
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    flags = observed_id_flags(result_rows)
    budgets = sorted({int(finite_number(row.get("short_budget_ms"), -1)) for row in result_rows})
    contexts_seen = {str(row.get("normalized_context_key", "")) for row in result_rows}
    expected_rows = len(contexts) * len(candidates) * len(PRIMARY_BUDGETS)
    recognition = candidate_recognition_counts(result_rows, set(candidates))
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    external_status = external_lacam2_solver_status(root)
    gates = {
        "probe_ran": bool(result_rows),
        "rows_eq_expected": len(result_rows) == expected_rows,
        "contexts_eq_60": len(contexts_seen) == 60,
        "candidate_count_le_30": len(candidates) <= 30,
        "budgets_eq_1000_2000": budgets == PRIMARY_BUDGETS,
        "candidate_recognized_all": recognition["candidate_recognized_all"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "external_lacam2_solver_untouched": not external_status,
    }
    integrity_decision = "full_primary_confirmation_integrity_passed_continue_v10_targets" if all(gates.values()) else "full_primary_confirmation_integrity_failed"
    integrity = {
        "schema_version": "phase5p5_repair5g521_full_primary_confirmation_integrity_summary_v1",
        "decision": integrity_decision,
        "probe_ran": bool(result_rows),
        "probe_rows": len(result_rows),
        "expected_rows": expected_rows,
        "contexts": len(contexts_seen),
        "candidate_count": len(candidates),
        "old14_candidate_count": len(old_controls),
        "g518_retained_candidate_count": len(retained_g518),
        "g521_selected_candidate_count": len(selected_g521),
        "checkpoint_rows": len(checkpoint_rows),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "recognition": recognition,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(results_csv),
        "gates": gates,
        **flags,
        **G521_CLOSED_CLAIMS,
    }
    oracle, oracle_rows, distribution = summarize_oracle(result_rows, set(old_controls), set(retained_g518), set(selected_g521))
    oracle["integrity_decision"] = integrity_decision
    write_json_file(args.integrity_summary_json, integrity)
    write_json_file(args.oracle_summary_json, oracle)
    write_rows(args.oracle_by_context_csv, oracle_rows)
    write_rows(args.candidate_distribution_csv, distribution)
    write_text_file(
        args.integrity_report,
        "# Repair5G.5.21 Full-Primary Confirmation Integrity\n\n"
        f"- decision: `{integrity_decision}`\n"
        f"- probe_rows: `{len(result_rows)}`\n"
        f"- expected_rows: `{expected_rows}`\n"
        f"- contexts: `{len(contexts_seen)}`\n"
        f"- candidate_count: `{len(candidates)}`\n"
        f"- gates: `{gates}`\n",
    )
    write_text_file(
        args.oracle_report,
        "# Repair5G.5.21 Full-Primary Confirmation Oracle\n\n"
        f"- decision: `{oracle['decision']}`\n"
        f"- old14_vs_g51822_oracle_gap: `{csv_number(oracle['old14_vs_g51822_oracle_gap'])}`\n"
        f"- g51822_vs_g52130_oracle_gap: `{csv_number(oracle['g51822_vs_g52130_oracle_gap'])}`\n"
        f"- second_wave_win_contexts: `{oracle['second_wave_win_contexts']}`\n"
        f"- second_wave_safe_win_contexts: `{oracle['second_wave_safe_win_contexts']}`\n"
        f"- mean_delta_vs_static: `{csv_number(oracle['mean_delta_vs_static'])}`\n"
        f"- mean_delta_vs_additive: `{csv_number(oracle['mean_delta_vs_additive'])}`\n",
    )
    print(json.dumps({"decision": integrity_decision, "probe_rows": len(result_rows), "candidate_count": len(candidates)}))
    return 0 if integrity_decision != "full_primary_confirmation_integrity_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
