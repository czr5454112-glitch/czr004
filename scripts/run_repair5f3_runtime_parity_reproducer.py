"""Rerun Repair5F.3 runtime parity mismatch cases.

The runner replays only the mismatch cases identified by
``analyze_repair5f3_runtime_parity.py`` plus one known-good control case. It is
diagnostic-only and does not run any larger validation scope.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402
from run_repair5f_runtime_export_eval import MAPS, dirty_state, git_value  # noqa: E402


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5f3_runtime_parity_autopsy_summary.json"
DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5f3_runtime_parity_reproducer"
DEFAULT_OUTPUT_JSONL = (
    "outputs/logs/phase5p5_repair5f3_runtime_parity_reproducer/"
    "phase5p5_repair5f3_runtime_parity_reproducer.jsonl"
)
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f3_runtime_parity_reproducer_report.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5f3_runtime_parity_reproducer_summary.json"
DEFAULT_PAIRED_CSV = "outputs/tables/phase5p5_repair5f3_runtime_parity_reproducer_paired.csv"

BASE_METHOD = "lacam_star_ltm"
OUTCOME_FIELDS = ["success", "feasible", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]
EFFORT_FIELDS = [
    "returned_solutions_count",
    "ltm_iterations",
    "expanded_nodes",
    "high_level_expansions",
    "low_level_pibt_calls",
]
DEFAULT_CONTROL_CASE = ("maze-32-32-4", 50, 21)


@dataclass(frozen=True)
class MethodSpec:
    method: str
    alias: str
    extra_args: tuple[str, ...] = ()


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def number(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)))


def parse_case(value: str) -> tuple[str, int, int]:
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError("--case and --control-case must use map:agents:seed")
    return (parts[0], int(parts[1]), int(parts[2]))


def load_cases(
    *,
    autopsy_summary: Path,
    explicit_cases: list[str],
    control_case: str,
) -> list[tuple[str, int, int]]:
    cases = [parse_case(value) for value in explicit_cases]
    if not cases:
        summary = read_json(autopsy_summary)
        cases = [
            (str(item["map"]), int(item["agents"]), int(item["seed"]))
            for item in summary.get("core_mismatch_cases", [])
        ]
    control = parse_case(control_case) if control_case else DEFAULT_CONTROL_CASE
    cases.append(control)
    return sorted(set(cases), key=lambda item: (item[0], item[1], item[2]))


def build_reproducer_methods() -> list[MethodSpec]:
    return [
        MethodSpec("lacam_star_ltm", "lacam_star_ltm"),
        MethodSpec("always_additive_defer", "always_additive_defer"),
        MethodSpec("repair5f_candidate_additive_ltm", "repair5f_candidate_additive_ltm"),
        MethodSpec(
            "repair5f_bounded_updateparam_selector_force_additive_parity",
            "repair5f_bounded_updateparam_selector_force_additive_parity",
        ),
        MethodSpec("laur_disable", "laur_disable"),
        MethodSpec("laur_force_additive_direct", "laur_force_additive_direct"),
    ]


def run_cases(
    *,
    root: Path,
    binary: Path,
    scenario_dir: Path,
    output_jsonl: Path,
    command_log: Path,
    update_log: Path,
    cases: list[tuple[str, int, int]],
    methods: list[MethodSpec],
    repeats: int,
    time_limit_sec: float,
    ltm_max_iterations: int,
) -> list[dict[str, Any]]:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    command_rows: list[dict[str, Any]] = []
    for repeat in range(1, repeats + 1):
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
                if spec.method != "lacam_star_ltm":
                    extra_args.extend(["--laur-update-log-jsonl", str(update_log)])
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
                    f"phase5p5-repair5f3-runtime-parity-reproducer-r{repeat}",
                    "--project-commit",
                    git_value(["rev-parse", "--short", "HEAD"], root),
                    "--external-commit",
                    "local",
                    "--branch",
                    git_value(["branch", "--show-current"], root),
                    "--dirty",
                    dirty_state(root),
                    "--platform",
                    "Windows Repair5F.3 parity reproducer",
                    *extra_args,
                ]
                completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
                row = {
                    "repeat": repeat,
                    "method": spec.alias,
                    "map": map_name,
                    "agents": int(agents),
                    "seed": int(seed),
                    "returncode": completed.returncode,
                    "command": command,
                    "stdout": completed.stdout.strip()[-500:],
                    "stderr": completed.stderr.strip()[-500:],
                }
                command_rows.append(row)
                with command_log.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                if completed.returncode == 1:
                    raise RuntimeError(
                        f"solver crashed for {spec.alias} {map_name} a{agents} s{seed}: {completed.stderr}"
                    )
    return command_rows


def annotate_repeats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, int, int, str], int] = defaultdict(int)
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = normalize_run_row(raw)
        key = (*case_key(row), str(row.get("method")))
        counts[key] += 1
        row["repeat"] = counts[key]
        out.append(row)
    return out


def exact_fields(base: dict[str, Any] | None, other: dict[str, Any] | None, fields: list[str]) -> bool:
    if base is None or other is None:
        return False
    return all(base.get(field) == other.get(field) for field in fields)


def build_paired(rows: list[dict[str, Any]], methods: list[MethodSpec]) -> list[dict[str, Any]]:
    by_case_repeat: dict[tuple[str, int, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (*case_key(row), int(row.get("repeat") or 0))
        by_case_repeat[key][str(row.get("method"))] = row
    paired: list[dict[str, Any]] = []
    for key, method_rows in sorted(by_case_repeat.items()):
        base = method_rows.get(BASE_METHOD)
        base_ratio = number(base.get("sum_of_loss_ratio") if base else None)
        for spec in methods:
            method = spec.alias
            if method == BASE_METHOD:
                continue
            row = method_rows.get(method)
            ratio = number(row.get("sum_of_loss_ratio") if row else None)
            delta = ratio - base_ratio if math.isfinite(ratio) and math.isfinite(base_ratio) else math.nan
            paired.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "repeat": key[3],
                    "method": method,
                    "present": row is not None,
                    "outcome_exact": exact_fields(base, row, OUTCOME_FIELDS),
                    "effort_exact": exact_fields(base, row, EFFORT_FIELDS),
                    "success": row.get("success") if row else "",
                    "ltm_success": base.get("success") if base else "",
                    "sum_of_loss_ratio": ratio if math.isfinite(ratio) else "",
                    "ltm_sum_of_loss_ratio": base_ratio if math.isfinite(base_ratio) else "",
                    "delta_ratio_vs_ltm": delta if math.isfinite(delta) else "",
                    "laur_update_mode": row.get("laur_update_mode", "") if row else "",
                    "laur_force_additive": row.get("laur_force_additive", "") if row else "",
                    "laur_model_path": row.get("laur_model_path", "") if row else "",
                }
            )
    return paired


def summarize_parity(paired: list[dict[str, Any]], methods: list[MethodSpec]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for spec in methods:
        method = spec.alias
        if method == BASE_METHOD:
            continue
        rows = [row for row in paired if row["method"] == method]
        deltas = [number(row.get("delta_ratio_vs_ltm")) for row in rows]
        out[method] = {
            "rows": len(rows),
            "outcome_exact": bool(rows) and all(boolish(row.get("outcome_exact")) for row in rows),
            "effort_exact": bool(rows) and all(boolish(row.get("effort_exact")) for row in rows),
            "better": sum(1 for value in deltas if math.isfinite(value) and value < -1.0e-12),
            "equal": sum(1 for value in deltas if math.isfinite(value) and abs(value) <= 1.0e-12),
            "worse": sum(1 for value in deltas if math.isfinite(value) and value > 1.0e-12),
        }
    return out


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Repair5F.3 Runtime Parity Reproducer\n\n")
        handle.write("Diagnostic-only. This reruns only parity mismatch cases plus one control case.\n\n")
        handle.write("## Scope\n\n")
        handle.write(f"- repeats: `{summary['repeats']}`\n")
        handle.write(f"- cases: `{summary['cases']}`\n")
        handle.write(f"- methods: `{summary['methods']}`\n")
        handle.write("\n## Parity\n\n")
        handle.write("| method | rows | outcome exact | effort exact | better | equal | worse |\n")
        handle.write("|---|---:|---|---|---:|---:|---:|\n")
        for method, row in summary["parity_by_method"].items():
            handle.write(
                f"| `{method}` | {row['rows']} | {row['outcome_exact']} | {row['effort_exact']} | "
                f"{row['better']} | {row['equal']} | {row['worse']} |\n"
            )
        handle.write("\n## Interpretation\n\n")
        if summary["all_outcome_parity_exact"]:
            handle.write("All replayed parity controls match plain LaCAM*+LTM on outcome fields.\n")
        else:
            handle.write("At least one replayed parity control still diverges on outcome fields.\n")
        handle.write("No Phase5.5 or Phase6 permission is granted by this reproducer.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY_SUMMARY))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED_CSV))
    parser.add_argument("--case", action="append", default=[], help="map:agents:seed")
    parser.add_argument("--control-case", default="maze-32-32-4:50:21")
    parser.add_argument("--repeats", type=int, default=3)
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
    output_dir = resolve(args.output_dir, root)
    output_jsonl = resolve(args.output_jsonl, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    paired_csv = resolve(args.paired_csv, root)
    command_log = output_jsonl.with_name(output_jsonl.stem + "_commands.jsonl")
    update_log = output_jsonl.with_name(output_jsonl.stem + "_laur_updates.jsonl")

    if args.repeats < 1:
        raise ValueError("--repeats must be >= 1")
    cases = load_cases(
        autopsy_summary=autopsy_summary,
        explicit_cases=list(args.case),
        control_case=str(args.control_case),
    )
    methods = build_reproducer_methods()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
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
            update_log=update_log,
            cases=cases,
            methods=methods,
            repeats=int(args.repeats),
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
        )

    raw_rows = read_jsonl(output_jsonl)
    rows = annotate_repeats(raw_rows)
    schema_errors: list[str] = []
    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))
    paired = build_paired(rows, methods)
    paired_fields = [
        "map",
        "agents",
        "seed",
        "repeat",
        "method",
        "present",
        "outcome_exact",
        "effort_exact",
        "success",
        "ltm_success",
        "sum_of_loss_ratio",
        "ltm_sum_of_loss_ratio",
        "delta_ratio_vs_ltm",
        "laur_update_mode",
        "laur_force_additive",
        "laur_model_path",
    ]
    write_csv(paired_csv, paired, paired_fields)
    parity = summarize_parity(paired, methods)
    update_rows = read_jsonl(update_log)
    summary = {
        "schema_version": "phase5p5_repair5f3_runtime_parity_reproducer_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "cases": [{"map": item[0], "agents": item[1], "seed": item[2]} for item in cases],
        "methods": [method.alias for method in methods],
        "repeats": int(args.repeats),
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "raw_jsonl": rel(output_jsonl, root),
        "command_log_jsonl": rel(command_log, root),
        "laur_update_log_jsonl": rel(update_log, root),
        "paired_csv": rel(paired_csv, root),
        "report": rel(report, root),
        "summary_json": rel(summary_json, root),
        "raw_rows": len(raw_rows),
        "annotated_rows": len(rows),
        "schema_errors": schema_errors,
        "laur_update_log_rows": len(update_rows),
        "parity_by_method": parity,
        "all_outcome_parity_exact": all(row["outcome_exact"] for row in parity.values()),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"summary_json": rel(summary_json, root), "all_outcome_parity_exact": summary["all_outcome_parity_exact"]}))
    return 0 if not schema_errors else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
