"""Sequential reproducer for Repair5G.3 strict control parity failures."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g31_protocol_common import (  # noqa: E402
    ALLOWED_NON_SEMANTIC_CLASSIFICATIONS,
    CONTROL_METHODS,
    CONTROL_PAIRS,
    classify_returncode,
    classify_strict_mismatch,
    command_key,
    number,
    solver_crash_count,
    strict_mismatched_fields,
)
from repair5g2_common import run_one_solver_task  # noqa: E402
from repair5g3_common import (  # noqa: E402
    AGENTS,
    MAPS,
    audit_and_prepare_scenarios,
    build_specs,
    now_iso,
    read_csv_rows,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    schema_error_count,
    write_csv_rows,
    write_json,
    write_jsonl,
)


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g3_scenarios"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g31_runtimes"
DEFAULT_MISMATCH_CSV = "outputs/tables/phase5p5_repair5g3_protocol_parity_mismatch_cases.csv"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g31_control_parity_reproducer"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g31_control_parity_reproducer.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g31_control_parity_reproducer_commands.jsonl"
DEFAULT_PAIRS = "outputs/tables/phase5p5_repair5g31_control_parity_reproducer_pairs.csv"
DEFAULT_BY_MODE = "outputs/tables/phase5p5_repair5g31_control_parity_reproducer_by_mode.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g31_control_parity_reproducer_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g31_control_parity_reproducer_summary.json"

SEQUENTIAL_MODES = [
    {"mode": "A_seq_3s_r3", "time_limit_sec": 3.0, "repeats": 3, "max_workers": 1},
    {"mode": "B_seq_5s_r2", "time_limit_sec": 5.0, "repeats": 2, "max_workers": 1},
    {"mode": "C_seq_10s_r1", "time_limit_sec": 10.0, "repeats": 1, "max_workers": 1},
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--mismatch-csv", type=Path, default=Path(DEFAULT_MISMATCH_CSV))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--pairs-csv", type=Path, default=Path(DEFAULT_PAIRS))
    parser.add_argument("--by-mode-csv", type=Path, default=Path(DEFAULT_BY_MODE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--include-sentinel", action="store_true")
    parser.add_argument("--sentinel-instance-ids", nargs="+", type=int, default=list(range(106, 116)))
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--modes", nargs="+", default=[row["mode"] for row in SEQUENTIAL_MODES])
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def mismatch_cases(path: Path) -> list[dict[str, Any]]:
    rows = read_csv_rows(path)
    seen: set[tuple[str, int, int, str]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("source") != "g3_broader":
            continue
        key = (
            str(row.get("map")),
            int(float(row.get("agents", 0) or 0)),
            int(float(row.get("seed", 0) or 0)),
            str(row.get("scen", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append({"map": key[0], "agents": key[1], "seed": key[2], "scen": key[3], "case_source": "g3_mismatch"})
    return out


def sentinel_cases(instance_ids: list[int]) -> list[dict[str, Any]]:
    return [
        {"map": map_name, "agents": agents, "seed": seed, "scen": f"{map_name}-random-{seed}.scen", "case_source": "sentinel"}
        for map_name in MAPS
        for agents in AGENTS
        for seed in instance_ids
    ]


def completed_task_keys(rows: list[dict[str, Any]]) -> set[tuple[Any, ...]]:
    return {
        (
            row.get("mode"),
            int(number(row.get("repeat_index"), 0)),
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            str(row.get("method")),
        )
        for row in rows
    }


def attach_returncodes(rows: list[dict[str, Any]], commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for command in commands:
        key = (
            command.get("mode"),
            int(number(command.get("repeat_index"), 0)),
            *command_key(command),
        )
        by_key[key] = command
    out = []
    for row in rows:
        item = dict(row)
        command = by_key.get(
            (
                row.get("mode"),
                int(number(row.get("repeat_index"), 0)),
                *command_key(row),
            ),
            {},
        )
        item["returncode"] = command.get("returncode", item.get("returncode", 0))
        item["returncode_classification"] = classify_returncode(item.get("returncode"))
        out.append(item)
    return out


def pair_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (
            row.get("mode"),
            int(number(row.get("repeat_index"), 0)),
            str(row.get("case_source", "")),
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            str(row.get("scen", "")),
        )
        grouped[key][str(row.get("method"))] = row
    out = []
    for key, methods in sorted(grouped.items()):
        for left_method, right_method in CONTROL_PAIRS:
            left = methods.get(left_method)
            right = methods.get(right_method)
            classification = classify_strict_mismatch(left, right)
            mismatched = strict_mismatched_fields(left or {}, right or {})
            item = {
                "mode": key[0],
                "repeat_index": key[1],
                "case_source": key[2],
                "map": key[3],
                "agents": key[4],
                "seed": key[5],
                "scen": key[6],
                "left_method": left_method,
                "right_method": right_method,
                "classification": classification,
                "mismatched_fields": ",".join(mismatched),
            }
            for prefix, row in [("left", left or {}), ("right", right or {})]:
                item.update(
                    {
                        f"{prefix}_returncode": row.get("returncode", ""),
                        f"{prefix}_success": row.get("success", ""),
                        f"{prefix}_sum_of_loss": row.get("sum_of_loss", ""),
                        f"{prefix}_ratio": row.get("sum_of_loss_ratio", ""),
                        f"{prefix}_makespan": row.get("makespan", ""),
                        f"{prefix}_expanded_nodes": row.get("expanded_nodes", ""),
                        f"{prefix}_time_to_first_solution_ms": row.get("time_to_first_solution_ms", ""),
                        f"{prefix}_runtime_ms": row.get("runtime_ms", ""),
                    }
                )
            out.append(item)
    return out


def by_mode_rows(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        grouped[str(row["mode"])].append(row)
    out = []
    for mode, rows in sorted(grouped.items()):
        counts = Counter(str(row["classification"]) for row in rows)
        out.append(
            {
                "mode": mode,
                "pair_rows": len(rows),
                "exact_pairs": counts.get("exact", 0),
                "strict_mismatch_pairs": len(rows) - counts.get("exact", 0),
                "true_semantic_parity_mismatch_count": counts.get("true_semantic_mismatch", 0),
                "time_budget_sensitivity": counts.get("time_budget_sensitivity", 0),
                "timeout_equivalent": counts.get("timeout_equivalent", 0),
                "returncode2_no_solution_equivalent": counts.get("returncode2_no_solution_equivalent", 0),
                "missing_row": counts.get("missing_row", 0),
                "classification_counts": json.dumps(dict(sorted(counts.items())), sort_keys=True),
            }
        )
    return out


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3.1 Control Parity Reproducer\n\n")
        handle.write("Control-only sequential reproducer for the G3 strict parity failure.\n\n")
        handle.write("## Result\n\n")
        handle.write(f"- protocol_reproducer_passed: `{summary['protocol_reproducer_passed']}`\n")
        handle.write(f"- true_semantic_parity_mismatch_count: `{summary['true_semantic_parity_mismatch_count']}`\n")
        handle.write(f"- strict_mismatch_classification_counts: `{summary['strict_mismatch_classification_counts']}`\n")
        handle.write(f"- solver_crash_count: `{summary['solver_crash_count']}`\n")
        handle.write(f"- cases: `{summary['case_count']}`\n")
        handle.write(f"- rows: `{summary['row_count']}`\n\n")
        handle.write("## Interpretation\n\n")
        handle.write(summary["interpretation"] + "\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    if args.overwrite:
        for path in [output_jsonl, command_log]:
            if path.exists():
                path.unlink()

    cases = mismatch_cases(resolve(args.mismatch_csv, root))
    sentinel_used = False
    if args.include_sentinel or not cases:
        cases.extend(sentinel_cases([int(value) for value in args.sentinel_instance_ids]))
        sentinel_used = True
    if args.max_cases and args.max_cases > 0:
        cases = cases[: int(args.max_cases)]
    if not cases:
        raise SystemExit("no mismatch or sentinel cases to reproduce")

    maps = sorted({str(row["map"]) for row in cases})
    agents = sorted({int(row["agents"]) for row in cases})
    seeds = sorted({int(row["seed"]) for row in cases})
    audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=resolve(args.scenario_dir, root),
        scenario_metadata=root / "outputs/reports/phase5p5_repair5g31_control_parity_reproducer_scenarios.json",
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
        generate_missing=True,
        base_seed=20260522,
    )

    specs = {spec.alias: spec for spec in build_specs(CONTROL_METHODS, resolve(args.runtime_root, root))}
    modes = [row for row in SEQUENTIAL_MODES if row["mode"] in set(args.modes)]
    existing_rows = read_jsonl(output_jsonl)
    existing_commands = read_jsonl(command_log)
    completed = completed_task_keys(existing_rows)
    new_rows: list[dict[str, Any]] = []
    new_commands: list[dict[str, Any]] = []
    temp_dir = output_jsonl.parent / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    for mode in modes:
        for repeat_index in range(int(mode["repeats"])):
            for case in cases:
                for method in CONTROL_METHODS:
                    task_key = (
                        mode["mode"],
                        repeat_index,
                        str(case["map"]),
                        int(case["agents"]),
                        int(case["seed"]),
                        method,
                    )
                    if task_key in completed:
                        continue
                    if args.skip_solver:
                        continue
                    rows, command = run_one_solver_task(
                        root=root,
                        binary=resolve(args.binary, root),
                        scenario_dir=resolve(args.scenario_dir, root),
                        temp_dir=temp_dir,
                        map_name=str(case["map"]),
                        agents=int(case["agents"]),
                        seed=int(case["seed"]),
                        time_limit_sec=float(mode["time_limit_sec"]),
                        ltm_max_iterations=int(args.ltm_max_iterations),
                        spec=specs[method],
                        manifest="phase5p5-repair5g31-control-parity-reproducer",
                    )
                    command = {
                        **command,
                        "mode": mode["mode"],
                        "repeat_index": repeat_index,
                        "time_budget_sec": float(mode["time_limit_sec"]),
                        "max_workers": int(mode["max_workers"]),
                        "case_source": case["case_source"],
                    }
                    for row in rows:
                        item = {
                            **row,
                            "mode": mode["mode"],
                            "repeat_index": repeat_index,
                            "time_budget_sec": float(mode["time_limit_sec"]),
                            "case_source": case["case_source"],
                        }
                        new_rows.append(item)
                    new_commands.append(command)
                    write_jsonl(output_jsonl, [*existing_rows, *new_rows])
                    write_jsonl(command_log, [*existing_commands, *new_commands])
    all_commands = read_jsonl(command_log)
    all_rows = attach_returncodes(read_jsonl(output_jsonl), all_commands)
    write_jsonl(output_jsonl, all_rows)
    pairs = pair_rows(all_rows)
    by_mode = by_mode_rows(pairs)
    write_csv_rows(resolve(args.pairs_csv, root), pairs)
    write_csv_rows(resolve(args.by_mode_csv, root), by_mode)
    mismatch_pairs = [row for row in pairs if row["classification"] != "exact"]
    counts = Counter(str(row["classification"]) for row in mismatch_pairs)
    true_semantic = counts.get("true_semantic_mismatch", 0)
    non_semantic_only = all(row["classification"] in ALLOWED_NON_SEMANTIC_CLASSIFICATIONS for row in mismatch_pairs)
    protocol_passed = (
        true_semantic == 0
        and non_semantic_only
        and solver_crash_count(all_commands) == 0
        and schema_error_count(all_rows) == 0
    )
    summary = {
        "schema_version": "phase5p5_repair5g31_control_parity_reproducer_summary_v1",
        "created_at": now_iso(),
        "case_count": len(cases),
        "case_sources": dict(sorted(Counter(str(row["case_source"]) for row in cases).items())),
        "sentinel_used": sentinel_used,
        "modes": modes,
        "methods": CONTROL_METHODS,
        "row_count": len(all_rows),
        "command_count": len(all_commands),
        "pair_count": len(pairs),
        "strict_mismatch_pair_count": len(mismatch_pairs),
        "strict_mismatch_classification_counts": dict(sorted(counts.items())),
        "true_semantic_parity_mismatch_count": true_semantic,
        "solver_crash_count": solver_crash_count(all_commands),
        "schema_errors": schema_error_count(all_rows),
        "by_mode": by_mode,
        "protocol_reproducer_passed": protocol_passed,
        "interpretation": (
            "Sequential control-only reproduction found no true semantic parity mismatch; remaining strict differences are classified as budget/timeout/return-code equivalence."
            if protocol_passed
            else "Sequential control-only reproduction did not close the protocol issue; stop before G4."
        ),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"protocol_reproducer_passed": protocol_passed, "rows": len(all_rows), "cases": len(cases)}))
    return 0 if protocol_passed else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
