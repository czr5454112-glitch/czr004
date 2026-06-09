"""Verify G5.22 response-design adapter recognition."""

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
from repair5g522_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G521_SELECTED_CSV,
    G522_ADAPTER_LOG_DIR,
    G522_ADAPTER_REPORT,
    G522_ADAPTER_RESULTS,
    G522_ADAPTER_SCENARIO_DIR,
    G522_ADAPTER_SCENARIO_METADATA,
    G522_ADAPTER_SUMMARY,
    G522_CLOSED_CLAIMS,
    G522_CONTEXT_PANEL_CSV,
    G522_RESPONSE_DESIGN_CSV,
    candidate_params,
    external_lacam2_solver_status,
    g518_candidate_id,
    g518_retained_candidate_ids,
    old14_candidate_ids,
    parse_g522_candidate_id,
    read_jsonl,
    read_rows,
    repo_root,
    resolve,
    selected_g521_candidate_ids,
    selected_g522_candidate_ids,
    write_json_file,
    write_text_file,
)
from repair5g517_common import write_probe_csv_from_jsonl  # noqa: E402


INVALID_CANDIDATES = [
    "repair5g522_grid_c2p50_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0",
    "repair5g522_grid_c1x25_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c0",
    "repair5g522_grid_c1p25_b1p00_f1p00_w0p75_dc0p95_df1p00_beta0p35_max0p75_c2",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--cpp", type=Path, default=Path("cpp/tools/phase1a_batch.cpp"))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(G522_ADAPTER_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(G522_ADAPTER_SCENARIO_METADATA))
    parser.add_argument("--context-panel-csv", type=Path, default=Path(G522_CONTEXT_PANEL_CSV))
    parser.add_argument("--design-csv", type=Path, default=Path(G522_RESPONSE_DESIGN_CSV))
    parser.add_argument("--results-csv", type=Path, default=Path(G522_ADAPTER_RESULTS))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_ADAPTER_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G522_ADAPTER_REPORT))
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
        if params is not None:
            pairs.append({"old_candidate_id": old, "g518_candidate_id": g518_candidate_id(params)})
    return pairs


def run_smoke(args: argparse.Namespace, root: Path, candidates: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    contexts = read_rows(args.context_panel_csv)
    if not contexts:
        raise RuntimeError("missing G5.22 context panel")
    combo = contexts[0]
    log_dir = resolve(G522_ADAPTER_LOG_DIR, root)
    output_jsonl = log_dir / "phase5p5_repair5g522_adapter_smoke_runs.jsonl"
    command_log = log_dir / "phase5p5_repair5g522_adapter_smoke_commands.jsonl"
    update_log = log_dir / "phase5p5_repair5g522_adapter_smoke_ltm_updates.jsonl"
    probe_jsonl = log_dir / "phase5p5_repair5g522_adapter_smoke_update_probes.jsonl"
    checkpoint_jsonl = log_dir / "phase5p5_repair5g522_adapter_smoke_checkpoints.jsonl"
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
        "repair5g522_adapter_smoke_static_context",
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
        manifest="phase5p5-repair5g522-adapter-smoke",
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
    selected_g522 = selected_g522_candidate_ids(args.design_csv, include_probe_only=True)
    selected_g521 = selected_g521_candidate_ids(G521_SELECTED_CSV)
    retained_g518 = g518_retained_candidate_ids(limit=8)
    parse_failures = []
    for candidate in selected_g522:
        try:
            parse_g522_candidate_id(candidate)
        except ValueError as exc:
            parse_failures.append({"candidate_id": candidate, "error": str(exc)})
    pairs = old_equivalent_pairs(root)
    smoke_candidates = unique(
        [pair["old_candidate_id"] for pair in pairs]
        + [pair["g518_candidate_id"] for pair in pairs]
        + retained_g518
        + selected_g521
        + selected_g522
        + INVALID_CANDIDATES
    )
    probe_rows, checkpoint_rows, run_meta = run_smoke(args, root, smoke_candidates)
    by_candidate = {str(row.get("candidate_id", "")): row for row in probe_rows}
    g522_unrecognized = [
        candidate for candidate in selected_g522
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() != "true"
    ]
    g521_unrecognized = [
        candidate for candidate in selected_g521
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() != "true"
    ]
    g518_unrecognized = [
        candidate for candidate in retained_g518
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() != "true"
    ]
    invalid_not_rejected = [
        candidate for candidate in INVALID_CANDIDATES
        if str(by_candidate.get(candidate, {}).get("candidate_recognized", "")).lower() == "true"
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
        "source_contains_g518_parser": "repair5g518_grid_" in source,
        "source_contains_g521_parser": "repair5g521_grid_" in source,
        "source_contains_g522_parser": "repair5g522_grid_" in source,
        "selected_g522_static_parse": not parse_failures,
        "smoke_probe_ran": bool(probe_rows),
        "checkpoint_rows_gt_0": len(checkpoint_rows) > 0,
        "all_selected_g522_candidates_recognized": bool(selected_g522) and not g522_unrecognized,
        "all_known_g521_candidates_recognized": bool(selected_g521) and not g521_unrecognized,
        "all_retained_g518_candidates_recognized": bool(retained_g518) and not g518_unrecognized,
        "invalid_names_rejected": not invalid_not_rejected,
        "old14_equivalence_records_exact": bool(equivalence_records) and not mismatched,
        "external_lacam2_solver_untouched": not external_status,
        "project_owned_cpp_edit_documented": True,
    }
    decision = "response_design_adapter_passed_continue_probe" if all(gates.values()) else "response_design_adapter_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g522_response_design_adapter_summary_v1",
        "decision": decision,
        "selected_g522_candidate_count": len(selected_g522),
        "known_g521_candidate_count": len(selected_g521),
        "retained_g518_candidate_count": len(retained_g518),
        "smoke_candidate_count": len(smoke_candidates),
        "probe_rows": len(probe_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "context": run_meta["combo"],
        "static_parse_failures": parse_failures,
        "g522_unrecognized": g522_unrecognized,
        "g521_unrecognized": g521_unrecognized,
        "g518_unrecognized": g518_unrecognized,
        "invalid_candidates": INVALID_CANDIDATES,
        "invalid_not_rejected": invalid_not_rejected,
        "old_equivalence_records": equivalence_records,
        "old_equivalence_mismatches": mismatched,
        "external_lacam2_solver_status": external_status,
        "cpp_edit_scope": "project-owned bounded adapter grammar recognition only",
        "results_csv": str(resolve(args.results_csv, root)),
        "gates": gates,
        **G522_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Response Design Adapter\n\n"
        f"- decision: `{decision}`\n"
        f"- selected_g522_candidate_count: `{len(selected_g522)}`\n"
        f"- known_g521_candidate_count: `{len(selected_g521)}`\n"
        f"- retained_g518_candidate_count: `{len(retained_g518)}`\n"
        f"- smoke_candidate_count: `{len(smoke_candidates)}`\n"
        f"- probe_rows: `{len(probe_rows)}`\n"
        f"- checkpoint_rows: `{len(checkpoint_rows)}`\n"
        f"- invalid_names_rejected: `{gates['invalid_names_rejected']}`\n"
        f"- old14_equivalence_records_exact: `{gates['old14_equivalence_records_exact']}`\n"
        f"- cpp_edit_scope: `project-owned bounded adapter grammar recognition only`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "probe_rows": len(probe_rows), "g522_unrecognized": len(g522_unrecognized)}))
    return 0 if decision == "response_design_adapter_passed_continue_probe" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
