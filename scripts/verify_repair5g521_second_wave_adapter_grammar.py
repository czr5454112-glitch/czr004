"""Verify the G5.21 second-wave bounded adapter grammar."""

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
from repair5g521_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G521_ADAPTER_LOG_DIR,
    G521_ADAPTER_REPORT,
    G521_ADAPTER_RESULTS,
    G521_ADAPTER_SCENARIO_DIR,
    G521_ADAPTER_SCENARIO_METADATA,
    G521_ADAPTER_SUMMARY,
    G521_CLOSED_CLAIMS,
    G521_SELECTED_CSV,
    candidate_params,
    external_lacam2_solver_status,
    g518_candidate_id,
    g518_retained_candidate_ids,
    old14_candidate_ids,
    parse_g521_candidate_id,
    read_rows,
    repo_root,
    resolve,
    selected_g521_candidate_ids,
    write_json_file,
    write_probe_csv_from_jsonl,
    write_text_file,
)


INVALID_CANDIDATES = [
    "repair5g521_grid_c2p50_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0",
    "repair5g521_grid_c1x25_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0",
    "repair5g521_grid_c1p25_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c2",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--cpp", type=Path, default=Path("cpp/tools/phase1a_batch.cpp"))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(G521_ADAPTER_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(G521_ADAPTER_SCENARIO_METADATA))
    parser.add_argument("--selected-csv", type=Path, default=Path(G521_SELECTED_CSV))
    parser.add_argument("--target-contexts-csv", type=Path, default=Path(G520_SECOND_WAVE_CONTEXTS_CSV))
    parser.add_argument("--results-csv", type=Path, default=Path(G521_ADAPTER_RESULTS))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_ADAPTER_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G521_ADAPTER_REPORT))
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


def old_equivalent_pairs(root: Path) -> list[dict[str, str]]:
    pairs = []
    for old in old14_candidate_ids(root):
        params = candidate_params(old)
        if params is None:
            continue
        pairs.append({"old_candidate_id": old, "g518_candidate_id": g518_candidate_id(params)})
    return pairs


def run_smoke(args: argparse.Namespace, root: Path, candidates: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    contexts = read_rows(args.target_contexts_csv)
    if not contexts:
        raise RuntimeError("missing G5.20 second-wave target contexts")
    combo = contexts[0]
    log_dir = resolve(G521_ADAPTER_LOG_DIR, root)
    output_jsonl = log_dir / "phase5p5_repair5g521_adapter_smoke_runs.jsonl"
    command_log = log_dir / "phase5p5_repair5g521_adapter_smoke_commands.jsonl"
    update_log = log_dir / "phase5p5_repair5g521_adapter_smoke_ltm_updates.jsonl"
    probe_jsonl = log_dir / "phase5p5_repair5g521_adapter_smoke_update_probes.jsonl"
    checkpoint_jsonl = log_dir / "phase5p5_repair5g521_adapter_smoke_checkpoints.jsonl"
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
        maps=[str(combo["map"])],
        agent_counts=[int(float(combo["agents"]))],
        instance_ids=[int(float(combo["seed"]))],
    )
    spec = MethodSpec(
        "repair5g59_static_flow_shield",
        "repair5g521_adapter_smoke_static_context",
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
        agents=int(float(combo["agents"])),
        seed=int(float(combo["seed"])),
        time_limit_sec=float(args.time_limit_sec),
        ltm_max_iterations=int(args.ltm_max_iterations),
        spec=spec,
        manifest="phase5p5-repair5g521-adapter-smoke",
    )
    for row in solver_rows:
        append_jsonl(output_jsonl, row)
    append_jsonl(command_log, command_row)
    probe_rows = write_probe_csv_from_jsonl(probe_jsonl, results_csv)
    return probe_rows, read_jsonl(checkpoint_jsonl), {"combo": combo, "command_row": command_row}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source = resolve(args.cpp, root).read_text(encoding="utf-8")
    selected = selected_g521_candidate_ids(args.selected_csv)
    static_parse_failures = []
    for candidate in selected:
        try:
            parse_g521_candidate_id(candidate)
        except ValueError as exc:
            static_parse_failures.append({"candidate_id": candidate, "error": str(exc)})
    pairs = old_equivalent_pairs(root)
    retained_g518 = g518_retained_candidate_ids(limit=8)
    smoke_candidates = unique(
        [pair["old_candidate_id"] for pair in pairs]
        + [pair["g518_candidate_id"] for pair in pairs]
        + retained_g518
        + selected
        + INVALID_CANDIDATES
    )
    probe_rows, checkpoint_rows, run_meta = run_smoke(args, root, smoke_candidates)
    by_candidate = {str(row.get("candidate_id", "")): row for row in probe_rows}
    selected_unrecognized = [
        candidate
        for candidate in selected
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() != "true"
    ]
    invalid_not_rejected = [
        candidate
        for candidate in INVALID_CANDIDATES
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() == "true"
    ]
    retained_unrecognized = [
        candidate
        for candidate in retained_g518
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() != "true"
    ]
    equivalence_records = []
    mismatched = []
    for pair in pairs:
        old_row = by_candidate.get(pair["old_candidate_id"], {})
        g518_row = by_candidate.get(pair["g518_candidate_id"], {})
        exact = bool(old_row) and bool(g518_row) and old_row.get("updateparams_fingerprint") == g518_row.get("updateparams_fingerprint")
        if not exact:
            mismatched.append(pair)
        equivalence_records.append(
            {
                **pair,
                "old_recognized": old_row.get("candidate_recognized", ""),
                "g518_recognized": g518_row.get("candidate_recognized", ""),
                "updateparams_fingerprint_exact": exact,
                "old_updateparams_hash": old_row.get("updateparams_hash", ""),
                "g518_updateparams_hash": g518_row.get("updateparams_hash", ""),
            }
        )
    external_status = external_lacam2_solver_status(root)
    gates = {
        "source_contains_g518_parser": "parse_g518_grid_lattice" in source and "repair5g518_grid_" in source,
        "source_contains_g521_parser": "repair5g521_grid_" in source,
        "selected_candidates_static_parse": not static_parse_failures,
        "smoke_probe_ran": bool(probe_rows),
        "checkpoint_rows_gt_0": len(checkpoint_rows) > 0,
        "all_selected_g521_candidates_recognized": bool(selected) and not selected_unrecognized,
        "all_retained_g518_candidates_recognized": bool(retained_g518) and not retained_unrecognized,
        "invalid_names_rejected": not invalid_not_rejected,
        "known_g518_fingerprints_unchanged": not mismatched and bool(equivalence_records),
        "external_lacam2_solver_untouched": not external_status,
        "max_workers_eq_1": True,
    }
    decision = "adapter_grammar_passed_continue_targeted_probe" if all(gates.values()) else "g521_adapter_grammar_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g521_second_wave_adapter_grammar_summary_v1",
        "decision": decision,
        "selected_g521_candidate_count": len(selected),
        "retained_g518_candidate_count": len(retained_g518),
        "smoke_candidate_count": len(smoke_candidates),
        "probe_rows": len(probe_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "context": run_meta["combo"],
        "static_parse_failures": static_parse_failures,
        "selected_unrecognized": selected_unrecognized,
        "retained_g518_unrecognized": retained_unrecognized,
        "invalid_candidates": INVALID_CANDIDATES,
        "invalid_not_rejected": invalid_not_rejected,
        "old_equivalence_records": equivalence_records,
        "old_equivalence_mismatches": mismatched,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(resolve(args.results_csv, root)),
        "gates": gates,
        **G521_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    equivalence_lines = "\n".join(
        f"- `{row['old_candidate_id']}` -> `{row['g518_candidate_id']}` exact=`{row['updateparams_fingerprint_exact']}`"
        for row in equivalence_records
    )
    write_text_file(
        args.report,
        "# Repair5G.5.21 Second-Wave Adapter Grammar\n\n"
        f"- decision: `{decision}`\n"
        f"- selected_g521_candidate_count: `{len(selected)}`\n"
        f"- retained_g518_candidate_count: `{len(retained_g518)}`\n"
        f"- smoke_candidate_count: `{len(smoke_candidates)}`\n"
        f"- probe_rows: `{len(probe_rows)}`\n"
        f"- invalid_names_rejected: `{gates['invalid_names_rejected']}`\n"
        f"- known_g518_fingerprints_unchanged: `{gates['known_g518_fingerprints_unchanged']}`\n"
        f"- gates: `{gates}`\n\n"
        "## Old Equivalent Checks\n\n"
        f"{equivalence_lines}\n\n"
        "This check exercises project-owned bounded UpdateParams adapter recognition only. Invalid names are expected to be marked `candidate_recognized=false` by the diagnostic probe.\n",
    )
    print(json.dumps({"decision": decision, "probe_rows": len(probe_rows), "selected_unrecognized": len(selected_unrecognized)}))
    return 0 if decision == "adapter_grammar_passed_continue_targeted_probe" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
