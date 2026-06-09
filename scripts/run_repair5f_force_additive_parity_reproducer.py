"""Rerun the Repair5F force-additive mismatch rows.

This runner is deliberately small: it replays only the cases identified by the
autopsy report and compares plain LaCAM*+LTM, the legacy force-additive alias,
the exact additive bounded candidate, ``--laur-disable``, and a direct
``--laur-force-additive`` path.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from create_repair5f_updateparam_candidates import build_candidates  # noqa: E402
from run_repair5f_updateparam_probe_table import (  # noqa: E402
    MAPS,
    MethodSpec,
    dirty_state,
    exact_additive_candidate_parity_exact,
    git_value,
    method_parity_exact,
    paired_method_stats,
    paired_rows,
    read_jsonl,
    write_candidate_runtime,
)
from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_AUTOPSY_SUMMARY = (
    "outputs/reports/phase5p5_repair5f_force_additive_parity_autopsy_summary.json"
)
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5f_force_additive_reproducer_runtimes"
DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5f_force_additive_reproducer"
DEFAULT_OUTPUT_JSONL = (
    "outputs/logs/phase5p5_repair5f_force_additive_reproducer/"
    "phase5p5_repair5f_force_additive_reproducer.jsonl"
)
DEFAULT_ADDITIVE_RUNTIME = "configs/phase5/laur_additive_only"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_force_additive_reproducer_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_force_additive_reproducer_summary.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(row.get("agents") or 0), int(row.get("seed") or 0))


def load_cases(path: Path, explicit_cases: list[str]) -> list[tuple[str, int, int]]:
    cases: list[tuple[str, int, int]] = []
    for value in explicit_cases:
        parts = value.split(":")
        if len(parts) != 3:
            raise ValueError("--case must use map:agents:seed")
        cases.append((parts[0], int(parts[1]), int(parts[2])))
    if cases:
        return cases

    summary = read_json(path)
    for item in summary.get("mismatch_cases", []):
        cases.append((str(item["map"]), int(item["agents"]), int(item["seed"])))
    return sorted(set(cases))


def build_reproducer_methods(
    *, runtime_root: Path, additive_runtime: Path
) -> list[MethodSpec]:
    additive_candidate = next(item for item in build_candidates() if item.candidate_id == "additive_ltm")
    additive_candidate_runtime = write_candidate_runtime(runtime_root, additive_candidate)
    return [
        MethodSpec("lacam_star_ltm", "lacam_star_ltm"),
        MethodSpec(
            "lacam_star_lau_ltm",
            "always_additive_defer",
            ("--laur-force-additive", "--laur-model-path", str(additive_runtime)),
        ),
        MethodSpec(
            "lacam_star_lau_ltm",
            "repair5f_candidate_additive_ltm",
            ("--laur-model-path", str(additive_candidate_runtime), "--laur-safety-threshold", "1.01"),
        ),
        MethodSpec("lacam_star_lau_ltm", "laur_disable", ("--laur-disable",)),
        MethodSpec("lacam_star_lau_ltm", "laur_force_additive_direct", ("--laur-force-additive",)),
    ]


def run_cases(
    *,
    root: Path,
    binary: Path,
    scenario_dir: Path,
    output_jsonl: Path,
    command_log: Path,
    laur_update_log: Path,
    cases: list[tuple[str, int, int]],
    methods: list[MethodSpec],
    time_limit_sec: float,
    ltm_max_iterations: int,
) -> list[dict[str, Any]]:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    command_rows: list[dict[str, Any]] = []
    for map_name, agents, seed in cases:
        if map_name not in MAPS:
            raise ValueError(f"unsupported map {map_name}")
        map_path = root / MAPS[map_name]
        scen_path = scenario_dir / f"{map_name}-random-{seed}.scen"
        if not map_path.exists():
            raise FileNotFoundError(map_path)
        if not scen_path.exists():
            raise FileNotFoundError(scen_path)
        for spec in methods:
            extra_args = list(spec.extra_args)
            if spec.method == "lacam_star_lau_ltm":
                extra_args.extend(["--laur-update-log-jsonl", str(laur_update_log)])
            command = [
                str(binary),
                "--method",
                spec.method,
                "--method-alias",
                spec.alias,
                "--map",
                str(map_path),
                "--scen",
                str(scen_path),
                "--agents",
                str(int(agents)),
                "--seed",
                str(int(seed)),
                "--time-limit-sec",
                str(float(time_limit_sec)),
                "--ltm-max-iterations",
                str(int(ltm_max_iterations)),
                "--output-jsonl",
                str(output_jsonl),
                "--map-name",
                map_name,
                "--scen-id",
                scen_path.name,
                "--manifest",
                "phase5p5-repair5f-force-additive-reproducer",
                "--project-commit",
                git_value(["rev-parse", "--short", "HEAD"], root),
                "--external-commit",
                "local",
                "--branch",
                git_value(["branch", "--show-current"], root),
                "--dirty",
                dirty_state(root),
                "--platform",
                "Windows Repair5F force-additive parity reproducer",
                *extra_args,
            ]
            completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
            row = {
                "method": spec.alias,
                "map": map_name,
                "agents": int(agents),
                "seed": int(seed),
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip()[-500:],
                "stderr": completed.stderr.strip()[-500:],
            }
            command_rows.append(row)
            with command_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            if completed.returncode != 0:
                raise RuntimeError(
                    f"solver failed for {spec.alias} {map_name} a{agents} seed{seed}: {completed.stderr}"
                )
    return command_rows


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int, int, str]] = set()
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = normalize_run_row(raw)
        key = (*case_key(row), str(row.get("method")))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def build_case_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "map",
        "agents",
        "seed",
        "method",
        "success",
        "sum_of_loss",
        "lower_bound",
        "sum_of_loss_ratio",
        "makespan",
        "expanded_nodes",
        "low_level_pibt_calls",
        "returned_solutions_count",
        "time_to_first_solution_ms",
        "ltm_iterations",
        "laur_enabled",
        "laur_force_additive",
        "laur_update_mode",
        "laur_post_first_solution_only",
        "laur_selected_rules",
        "laur_additive_fallback_count",
        "laur_inference_count",
    ]
    return [{field: row.get(field) for field in fields} for row in rows]


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Force-Additive Reproducer\n\n")
        handle.write("This reproducer reruns only the force-additive mismatch row(s).\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- selector_runtime_exported: `false`\n\n")
        handle.write("## Cases\n\n")
        for case in summary["cases"]:
            handle.write(f"- `{case['map']}`, agents `{case['agents']}`, seed `{case['seed']}`\n")
        handle.write("\n## Parity\n\n")
        for method, exact in summary["parity_vs_ltm"].items():
            handle.write(f"- {method}: `{exact}`\n")
        handle.write("\n## Rows\n\n")
        handle.write(
            "| method | success | SoL | LB | ratio | makespan | expanded | pibt | ltm iters | mode | force |\n"
        )
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|\n")
        for row in summary["case_rows"]:
            handle.write(
                f"| {row.get('method')} | {row.get('success')} | {row.get('sum_of_loss')} | "
                f"{row.get('lower_bound')} | {row.get('sum_of_loss_ratio')} | {row.get('makespan')} | "
                f"{row.get('expanded_nodes')} | {row.get('low_level_pibt_calls')} | "
                f"{row.get('ltm_iterations')} | {row.get('laur_update_mode')} | "
                f"{row.get('laur_force_additive')} |\n"
            )
        handle.write("\n## Interpretation\n\n")
        if all(summary["parity_vs_ltm"].values()):
            handle.write(
                "All replayed controls match plain LaCAM*+LTM on the parity tuple. "
                "This closes the mismatch at reproducer scope.\n"
            )
        else:
            handle.write(
                "At least one replayed control still diverges from LaCAM*+LTM. "
                "Do not proceed to selector/runtime export.\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY_SUMMARY))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--additive-runtime-dir", type=Path, default=Path(DEFAULT_ADDITIVE_RUNTIME))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--case", action="append", default=[], help="map:agents:seed")
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve(args.binary, root)
    scenario_dir = resolve(args.scenario_dir, root)
    autopsy_summary = resolve(args.autopsy_summary_json, root)
    runtime_root = resolve(args.runtime_root, root)
    additive_runtime = resolve(args.additive_runtime_dir, root)
    output_dir = resolve(args.output_dir, root)
    output_jsonl = resolve(args.output_jsonl, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    command_log = output_jsonl.with_name(output_jsonl.stem + "_commands.jsonl")
    laur_update_log = output_jsonl.with_name(output_jsonl.stem + "_laur_updates.jsonl")

    cases = load_cases(autopsy_summary, list(args.case))
    if not cases:
        raise RuntimeError("no mismatch cases found; run the autopsy first or pass --case")
    methods = build_reproducer_methods(runtime_root=runtime_root, additive_runtime=additive_runtime)

    output_dir.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        for path in (output_jsonl, command_log, laur_update_log):
            if path.exists():
                path.unlink()
    if not args.skip_solver:
        if output_jsonl.exists():
            raise FileExistsError(f"output JSONL already exists: {output_jsonl}")
        if not binary.exists():
            raise FileNotFoundError(binary)
        run_cases(
            root=root,
            binary=binary,
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            laur_update_log=laur_update_log,
            cases=cases,
            methods=methods,
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
        )

    rows = dedupe(read_jsonl(output_jsonl))
    schema_errors: list[str] = []
    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))
    paired = paired_rows(rows)
    stats = paired_method_stats(paired)
    parity_vs_ltm = {
        method.alias: method_parity_exact(rows, method.alias)
        for method in methods
        if method.alias != "lacam_star_ltm"
    }
    parity_vs_ltm["repair5f_candidate_additive_ltm"] = exact_additive_candidate_parity_exact(rows)
    summary = {
        "schema_version": "phase5p5_repair5f_force_additive_reproducer_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "selector_runtime_exported": False,
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "cases": [{"map": item[0], "agents": item[1], "seed": item[2]} for item in cases],
        "methods": [method.alias for method in methods],
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "raw_jsonl": rel(output_jsonl, root),
        "command_log_jsonl": rel(command_log, root),
        "laur_update_log_jsonl": rel(laur_update_log, root),
        "raw_rows": len(read_jsonl(output_jsonl)),
        "deduped_rows": len(rows),
        "schema_errors": schema_errors,
        "paired_method_stats": stats,
        "parity_vs_ltm": parity_vs_ltm,
        "case_rows": build_case_rows(rows),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"report": rel(report, root), "summary_json": rel(summary_json, root), "raw_jsonl": rel(output_jsonl, root)}))
    return 0 if not schema_errors else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
