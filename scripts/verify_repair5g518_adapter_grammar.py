"""Verify and smoke the generic G5.18 bounded adapter grammar."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g510_common import read_jsonl  # noqa: E402
from repair5g517_common import write_probe_csv_from_jsonl  # noqa: E402
from repair5g518_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G518_ADAPTER_REPORT,
    G518_ADAPTER_SMOKE_RESULTS,
    G518_ADAPTER_SUMMARY,
    G518_CLOSED_CLAIMS,
    G518_SELECTED_CSV,
    candidate_params,
    context_combos_from_plan,
    external_lacam2_solver_status,
    g518_candidate_id,
    old14_candidate_ids,
    parse_g518_candidate_id,
    plan_rows,
    read_csv_dicts,
    repo_root,
    resolve,
    selected_rows,
    write_json_file,
    write_text_file,
)


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g518_adapter_smoke"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g518_adapter_smoke_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g518_adapter_smoke_scenario_generation.json"
DEFAULT_OUTPUT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g518_adapter_smoke_runs.jsonl"
DEFAULT_COMMAND_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g518_adapter_smoke_commands.jsonl"
DEFAULT_UPDATE_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g518_adapter_smoke_ltm_updates.jsonl"
DEFAULT_PROBE_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g518_adapter_smoke_update_probes.jsonl"
DEFAULT_CHECKPOINT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g518_adapter_smoke_checkpoints.jsonl"


INVALID_CANDIDATES = [
    "repair5g518_grid_c2p50_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0",
    "repair5g518_grid_c1x25_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0",
    "repair5g518_grid_c1p25_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c2",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--cpp", type=Path, default=Path("cpp/tools/phase1a_batch.cpp"))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--probe-plan-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--selected-csv", type=Path, default=Path(G518_SELECTED_CSV))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMAND_LOG))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATE_LOG))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBE_JSONL))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINT_JSONL))
    parser.add_argument("--results-csv", type=Path, default=Path(G518_ADAPTER_SMOKE_RESULTS))
    parser.add_argument("--summary-json", type=Path, default=Path(G518_ADAPTER_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G518_ADAPTER_REPORT))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def unique(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def selected_g518_candidates(rows: list[dict[str, Any]]) -> list[str]:
    return unique(
        [
            str(row.get("candidate_id", ""))
            for row in rows
            if str(row.get("row_type", "")) == "new_candidate"
        ]
    )


def old_equivalent_pairs(root: Path) -> list[dict[str, str]]:
    pairs = []
    for old in old14_candidate_ids(root):
        params = candidate_params(old)
        if params is None:
            continue
        pairs.append({"old_candidate_id": old, "g518_candidate_id": g518_candidate_id(params)})
    return pairs


def run_smoke(args: argparse.Namespace, root: Path, candidates: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    plan = plan_rows(resolve(args.probe_plan_csv, root))
    combo = context_combos_from_plan(plan, limit=1)[0]
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    probe_jsonl = resolve(args.probe_jsonl, root)
    checkpoint_jsonl = resolve(args.checkpoint_jsonl, root)
    results_csv = resolve(args.results_csv, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, results_csv]:
            path.unlink(missing_ok=True)
    temp_dir = output_jsonl.parent / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    command_log.parent.mkdir(parents=True, exist_ok=True)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=resolve(args.scenario_dir, root),
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=[str(combo["map"])],
        agent_counts=[int(combo["agents"])],
        instance_ids=[int(combo["seed"])],
    )
    spec = MethodSpec(
        "repair5g59_static_flow_shield",
        "repair5g518_adapter_smoke_static_context",
        (
            "--repair5g5-selector-spec",
            str(resolve(args.selector_spec_json, root)),
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
            "1000",
            "--repair5g-counterfactual-max-contexts",
            "1",
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )
    solver_rows, _updates, command_row = run_one_solver_task(
        root=root,
        binary=resolve(args.binary, root),
        scenario_dir=resolve(args.scenario_dir, root),
        temp_dir=temp_dir,
        update_log=update_log,
        map_name=str(combo["map"]),
        agents=int(combo["agents"]),
        seed=int(combo["seed"]),
        time_limit_sec=float(args.time_limit_sec),
        ltm_max_iterations=int(args.ltm_max_iterations),
        spec=spec,
        manifest="phase5p5-repair5g518-adapter-smoke",
    )
    for row in solver_rows:
        append_jsonl(output_jsonl, row)
    append_jsonl(command_log, command_row)
    probe_rows = write_probe_csv_from_jsonl(probe_jsonl, results_csv)
    checkpoints = read_jsonl(checkpoint_jsonl)
    return probe_rows, checkpoints, {"combo": combo, "command_row": command_row}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source = resolve(args.cpp, root).read_text(encoding="utf-8")
    selected = selected_rows(resolve(args.selected_csv, root))
    selected_candidates = selected_g518_candidates(selected)
    static_parse_failures = []
    for candidate in selected_candidates:
        try:
            parse_g518_candidate_id(candidate)
        except ValueError as exc:
            static_parse_failures.append({"candidate_id": candidate, "error": str(exc)})
    pairs = old_equivalent_pairs(root)
    smoke_candidates = unique(
        [pair["old_candidate_id"] for pair in pairs]
        + [pair["g518_candidate_id"] for pair in pairs]
        + selected_candidates
        + INVALID_CANDIDATES
    )
    probe_rows, checkpoint_rows, run_meta = run_smoke(args, root, smoke_candidates)
    by_candidate = {str(row.get("candidate_id", "")): row for row in probe_rows}
    selected_unrecognized = [
        candidate
        for candidate in selected_candidates
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() != "true"
    ]
    invalid_not_rejected = [
        candidate
        for candidate in INVALID_CANDIDATES
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() == "true"
    ]
    equivalence_records = []
    mismatched = []
    for pair in pairs:
        old_row = by_candidate.get(pair["old_candidate_id"], {})
        new_row = by_candidate.get(pair["g518_candidate_id"], {})
        exact = bool(old_row) and bool(new_row) and old_row.get("updateparams_fingerprint") == new_row.get("updateparams_fingerprint")
        if not exact:
            mismatched.append(pair)
        equivalence_records.append(
            {
                **pair,
                "old_recognized": old_row.get("candidate_recognized", ""),
                "g518_recognized": new_row.get("candidate_recognized", ""),
                "updateparams_fingerprint_exact": exact,
                "old_updateparams_hash": old_row.get("updateparams_hash", ""),
                "g518_updateparams_hash": new_row.get("updateparams_hash", ""),
            }
        )
    external_status = external_lacam2_solver_status(root)
    gates = {
        "source_contains_g518_parser": "parse_g518_grid_lattice" in source and "repair5g518_grid_" in source,
        "selected_candidates_static_parse": not static_parse_failures,
        "smoke_probe_ran": bool(probe_rows),
        "checkpoint_rows_gt_0": len(checkpoint_rows) > 0,
        "all_selected_g518_candidates_recognized": not selected_unrecognized and bool(selected_candidates),
        "invalid_names_rejected": not invalid_not_rejected,
        "old_known_equivalent_fingerprints_exact": not mismatched and bool(equivalence_records),
        "external_lacam2_solver_untouched": not external_status,
        "max_workers_eq_1": True,
    }
    decision = "adapter_grammar_passed_continue_probe_batches" if all(gates.values()) else "g518_adapter_grammar_failed"
    summary = {
        "schema_version": "phase5p5_repair5g518_adapter_grammar_summary_v1",
        "decision": decision,
        "selected_g518_candidate_count": len(selected_candidates),
        "smoke_candidate_count": len(smoke_candidates),
        "probe_rows": len(probe_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "context": run_meta["combo"],
        "static_parse_failures": static_parse_failures,
        "selected_unrecognized": selected_unrecognized,
        "invalid_candidates": INVALID_CANDIDATES,
        "invalid_not_rejected": invalid_not_rejected,
        "old_equivalence_records": equivalence_records,
        "old_equivalence_mismatches": mismatched,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(resolve(args.results_csv, root)),
        "gates": gates,
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    equivalence_lines = "\n".join(
        f"- `{row['old_candidate_id']}` -> `{row['g518_candidate_id']}` exact=`{row['updateparams_fingerprint_exact']}`"
        for row in equivalence_records
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.18 Adapter Grammar\n\n"
        f"- decision: `{decision}`\n"
        f"- selected_g518_candidate_count: `{len(selected_candidates)}`\n"
        f"- smoke_candidate_count: `{len(smoke_candidates)}`\n"
        f"- probe_rows: `{len(probe_rows)}`\n"
        f"- invalid_names_rejected: `{gates['invalid_names_rejected']}`\n"
        f"- old_known_equivalent_fingerprints_exact: `{gates['old_known_equivalent_fingerprints_exact']}`\n"
        f"- gates: `{gates}`\n\n"
        "## Old Equivalent Checks\n\n"
        f"{equivalence_lines}\n\n"
        "This check exercises only project-owned adapter recognition for bounded UpdateParams names. Unrecognized invalid names fall back to additive inside the diagnostic probe and are explicitly marked `candidate_recognized=false`.\n",
    )
    print(json.dumps({"decision": decision, "probe_rows": len(probe_rows), "selected_unrecognized": len(selected_unrecognized)}))
    return 0 if decision == "adapter_grammar_passed_continue_probe_batches" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
