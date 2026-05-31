"""Run a diagnostic-only Phase5.5 LAUR closed-loop preflight.

This runner executes the existing solver binary on a tiny MAPF scope and
summarizes the result. It is intentionally diagnostic-only: it never grants
Phase5.5 or Phase6 permission, and it records when Repair5C attention-native
composite/oracle replay are not yet executable as C++ runtime policies.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402

try:  # noqa: E402
    from export_phase5_laur_mlp_runtime import export_runtime_dir
except Exception:  # pragma: no cover - export is optional for blocked setups.
    export_runtime_dir = None  # type: ignore[assignment]


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_laur_diagnostic_preflight"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_laur_diagnostic_preflight_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_laur_diagnostic_preflight_report.md"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_laur_diagnostic_preflight_summary.csv"
DEFAULT_PAIRED_CSV = "outputs/tables/phase5p5_laur_diagnostic_preflight_paired.csv"
DEFAULT_REPAIR3_WEIGHTS = "artifacts/models/laur_ltm/full_repair3_stable_tie001_mlp/laur_mlp_v1_weights.json"
DEFAULT_REPAIR3_RUNTIME = "outputs/tmp/phase5/laur_repair3_stable_tie001_mlp_runtime"

MAPS = {
    "random-32-32-20": "external/lacam2/scripts/map/random-32-32-20.map",
    "maze-32-32-4": "external/lacam2/scripts/map/maze-32-32-4.map",
    "warehouse-10-20-10-2-1": "external/lacam2/scripts/map/warehouse-10-20-10-2-1.map",
}

NONADDITIVE_RULES = {
    "commit_heavy",
    "block_heavy",
    "block_light",
    "wait_light",
    "wait_heavy",
    "decay_095",
    "decay_090",
}


@dataclass(frozen=True)
class MethodSpec:
    method: str
    alias: str
    extra_args: tuple[str, ...] = ()
    diagnostic_note: str = ""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _mean(values: list[float]) -> float | None:
    finite_values = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.mean(finite_values) if finite_values else None


def _number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _jsonl_name(output_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"phase5p5_laur_diagnostic_preflight_{stamp}.jsonl"


def ensure_repair3_runtime(root: Path, weights: Path, runtime_dir: Path) -> tuple[Path | None, str]:
    required = [
        "features.txt",
        "rules.csv",
        "layer0_weight.csv",
        "rule_head_weight.csv",
        "rule_head_bias.csv",
    ]
    if all((runtime_dir / name).exists() for name in required):
        return runtime_dir, "existing_runtime_dir"
    if weights.exists() and export_runtime_dir is not None:
        export_runtime_dir(weights, runtime_dir)
        return runtime_dir, "exported_from_weights_json"
    if weights.exists():
        return None, "weights_exist_but_export_helper_unavailable"
    return None, "missing_repair3_weights_json"


def build_methods(
    *,
    root: Path,
    additive_model: Path,
    repair3_runtime: Path | None,
    include_static_proxies: bool,
) -> tuple[list[MethodSpec], list[dict[str, Any]]]:
    methods = [
        MethodSpec("lacam_star", "lacam_star"),
        MethodSpec("lacam_star_ltm", "lacam_star_ltm"),
        MethodSpec(
            "lacam_star_lau_ltm",
            "always_additive_defer",
            ("--laur-force-additive", "--laur-model-path", str(additive_model)),
            "force-additive/defer parity diagnostic",
        ),
    ]
    skipped: list[dict[str, Any]] = []
    if repair3_runtime is not None:
        methods.append(
            MethodSpec(
                "lacam_star_lau_ltm",
                "repair3_safe_runtime",
                ("--laur-model-path", str(repair3_runtime), "--laur-safety-threshold", "0.30"),
                "conservative Repair3 runtime reference",
            )
        )
    else:
        skipped.append({"method": "repair3_safe_runtime", "reason": "runtime_model_unavailable"})

    if include_static_proxies:
        for rule in ("block_heavy", "wait_light", "decay_095"):
            methods.append(
                MethodSpec(
                    "lacam_star_lau_ltm",
                    f"static_{rule}",
                    ("--laur-static-rule", rule, "--laur-allow-pre-first-solution"),
                    "static rule proxy, not a learned Repair5C runtime",
                )
            )

    skipped.extend(
        [
            {
                "method": "repair5c_top3_per_rule_safety_utility_composite",
                "reason": "not_executed_attention_native_composite_has_no_cxx_runtime_export",
            },
            {
                "method": "oracle_replay_or_teacher_forced_update_choices",
                "reason": "not_feasible_no_closed_loop_teacher_force_hook",
            },
        ]
    )
    return methods, skipped


def run_solver_grid(
    *,
    root: Path,
    binary: Path,
    output_jsonl: Path,
    command_log: Path,
    maps: list[str],
    agent_counts: list[int],
    instances_per_setting: int,
    time_limit_sec: float,
    ltm_max_iterations: int,
    scenario_dir: Path,
    methods: list[MethodSpec],
) -> list[dict[str, Any]]:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    command_rows: list[dict[str, Any]] = []
    for map_name in maps:
        map_path = root / MAPS[map_name]
        if not map_path.exists():
            raise FileNotFoundError(f"missing map path {map_path}")
        for instance_id in range(1, int(instances_per_setting) + 1):
            scen_path = scenario_dir / f"{map_name}-random-{instance_id}.scen"
            if not scen_path.exists():
                raise FileNotFoundError(f"missing scenario path {scen_path}")
            for agents in agent_counts:
                for spec in methods:
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
                        str(instance_id),
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
                        "phase5p5-diagnostic-preflight",
                        "--project-commit",
                        git_value(["rev-parse", "--short", "HEAD"], root),
                        "--external-commit",
                        "local",
                        "--branch",
                        git_value(["branch", "--show-current"], root),
                        "--dirty",
                        dirty_state(root),
                        "--platform",
                        "Windows Phase5.5 LAUR diagnostic preflight",
                        *spec.extra_args,
                    ]
                    completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
                    row = {
                        "method": spec.alias,
                        "map": map_name,
                        "agents": agents,
                        "seed": instance_id,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout.strip()[-500:],
                        "stderr": completed.stderr.strip()[-500:],
                    }
                    command_rows.append(row)
                    with command_log.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(row, sort_keys=True) + "\n")
                    if completed.returncode == 1:
                        raise RuntimeError(f"solver crashed for {spec.alias} {map_name} a{agents} i{instance_id}: {completed.stderr}")
    return command_rows


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        grouped.setdefault((str(row["map"]), int(row["agents"]), str(row["method"])), []).append(row)

    summary: list[dict[str, Any]] = []
    for (map_name, agents, method), group in sorted(grouped.items()):
        ratios = [_number(row, "sum_of_loss_ratio") for row in group if row.get("success")]
        expanded = [_number(row, "expanded_nodes") for row in group]
        ttfs = [_number(row, "time_to_first_solution_ms") for row in group]
        returned = [_number(row, "returned_solutions_count") for row in group]
        pibt = [_number(row, "low_level_pibt_calls") for row in group]
        laur_ms = [_number(row, "laur_inference_total_ms") for row in group]
        inference_counts = [_number(row, "laur_inference_count") for row in group]
        fallback_counts = [_number(row, "laur_additive_fallback_count") for row in group]
        safety_counts = [_number(row, "laur_safety_disabled_count") for row in group]
        nonadditive_updates = 0
        total_update_decisions = 0
        selected_rules: dict[str, int] = {}
        for row in group:
            for rule, count in (row.get("laur_selected_rules") or {}).items():
                selected_rules[str(rule)] = selected_rules.get(str(rule), 0) + int(count)
                total_update_decisions += int(count)
                if str(rule) in NONADDITIVE_RULES:
                    nonadditive_updates += int(count)
            total_update_decisions += int(row.get("laur_additive_fallback_count") or 0)
        summary.append(
            {
                "map": map_name,
                "agents": agents,
                "method": method,
                "runs": len(group),
                "successes": sum(1 for row in group if row.get("success")),
                "success_rate": sum(1 for row in group if row.get("success")) / len(group) if group else 0.0,
                "sum_of_loss_ratio_mean": _mean([value for value in ratios if value is not None]),
                "expanded_nodes_mean": _mean([value for value in expanded if value is not None]),
                "time_to_first_solution_ms_mean": _mean([value for value in ttfs if value is not None]),
                "returned_solutions_count_mean": _mean([value for value in returned if value is not None]),
                "low_level_pibt_calls_mean": _mean([value for value in pibt if value is not None]),
                "laur_overhead_ms_mean": _mean([value for value in laur_ms if value is not None]),
                "laur_inference_count_mean": _mean([value for value in inference_counts if value is not None]),
                "laur_additive_fallback_count_mean": _mean([value for value in fallback_counts if value is not None]),
                "laur_safety_disabled_count_mean": _mean([value for value in safety_counts if value is not None]),
                "fallback_defer_rate": (
                    sum(value for value in fallback_counts if value is not None) / total_update_decisions
                    if total_update_decisions
                    else None
                ),
                "non_additive_update_rate": (
                    nonadditive_updates / total_update_decisions if total_update_decisions else None
                ),
                "selected_harmful_update_rate": None,
                "selected_rules": json.dumps(dict(sorted(selected_rules.items())), sort_keys=True),
            }
        )
    return summary


def paired_rows(rows: list[dict[str, Any]], baseline: str = "lacam_star_ltm") -> list[dict[str, Any]]:
    by_key: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        key = (row.get("map"), int(row.get("agents", 0)), row.get("seed"), row.get("scen"))
        by_key.setdefault(key, {})[str(row.get("method"))] = row

    pairs: list[dict[str, Any]] = []
    for key, methods in sorted(by_key.items()):
        if baseline not in methods:
            continue
        base = methods[baseline]
        for method, contender in sorted(methods.items()):
            if method == baseline:
                continue
            base_ratio = _number(base, "sum_of_loss_ratio")
            cont_ratio = _number(contender, "sum_of_loss_ratio")
            pairs.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "baseline_method": baseline,
                    "contender_method": method,
                    "baseline_success": bool(base.get("success")),
                    "contender_success": bool(contender.get("success")),
                    "baseline_ratio": base_ratio,
                    "contender_ratio": cont_ratio,
                    "delta_ratio": (
                        float(cont_ratio) - float(base_ratio)
                        if base_ratio is not None and cont_ratio is not None
                        else None
                    ),
                    "contender_better": (
                        bool(base.get("success"))
                        and bool(contender.get("success"))
                        and base_ratio is not None
                        and cont_ratio is not None
                        and float(cont_ratio) < float(base_ratio)
                    ),
                }
            )
    return pairs


def stop_condition_snapshot(summary_rows: list[dict[str, Any]], paired: list[dict[str, Any]]) -> dict[str, Any]:
    ltm_by_group = {
        (row["map"], int(row["agents"])): row
        for row in summary_rows
        if row["method"] == "lacam_star_ltm"
    }
    method_flags: dict[str, dict[str, Any]] = {}
    for row in summary_rows:
        method = str(row["method"])
        if method == "lacam_star_ltm":
            continue
        base = ltm_by_group.get((row["map"], int(row["agents"])))
        if not base:
            continue
        flags = method_flags.setdefault(
            method,
            {
                "success_worse_than_ltm_groups": 0,
                "ratio_worse_than_ltm_groups": 0,
                "zero_nonadditive_groups": 0,
            },
        )
        if float(row.get("success_rate") or 0.0) < float(base.get("success_rate") or 0.0):
            flags["success_worse_than_ltm_groups"] += 1
        ratio = row.get("sum_of_loss_ratio_mean")
        base_ratio = base.get("sum_of_loss_ratio_mean")
        if ratio is not None and base_ratio is not None and float(ratio) > float(base_ratio):
            flags["ratio_worse_than_ltm_groups"] += 1
        if row.get("non_additive_update_rate") == 0.0:
            flags["zero_nonadditive_groups"] += 1
    return {
        "method_flags": method_flags,
        "paired_rows": len(paired),
        "strict_safety_mask_blocks_all_learned_choices": any(
            row["method"] == "repair3_safe_runtime" and row.get("non_additive_update_rate") == 0.0
            for row in summary_rows
        ),
        "repair5c_composite_closed_loop_executed": False,
        "oracle_replay_executed": False,
    }


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 LAUR Diagnostic Preflight Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, "
            "does not permit Phase6, and does not change solver semantics.\n\n"
        )
        handle.write(f"- Phase5.5 allowed: `{summary.get('phase5p5_allowed')}`\n")
        handle.write(f"- Phase6 allowed: `{summary.get('phase6_allowed')}`\n")
        handle.write(f"- raw JSONL: `{summary.get('raw_jsonl')}`\n")
        handle.write(f"- command log: `{summary.get('command_log_jsonl')}`\n\n")

        handle.write("## Scope\n\n")
        scope = summary.get("scope", {})
        for key, value in scope.items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Runtime Availability\n\n")
        for skipped in summary.get("skipped_methods", []):
            handle.write(f"- `{skipped['method']}`: `{skipped['reason']}`\n")
        handle.write("\n## Group Summary\n\n")
        handle.write(
            "| map | agents | method | runs | success | ratio | expanded | TTFS ms | pibt | fallback | non-additive | overhead ms |\n"
        )
        handle.write("|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in summary.get("summary_rows", []):
            handle.write(
                f"| {row['map']} | {row['agents']} | {row['method']} | {row['runs']} | "
                f"{row['success_rate']:.6f} | {row.get('sum_of_loss_ratio_mean')} | "
                f"{row.get('expanded_nodes_mean')} | {row.get('time_to_first_solution_ms_mean')} | "
                f"{row.get('low_level_pibt_calls_mean')} | {row.get('fallback_defer_rate')} | "
                f"{row.get('non_additive_update_rate')} | {row.get('laur_overhead_ms_mean')} |\n"
            )
        handle.write("\n## Stop Condition Snapshot\n\n")
        handle.write(json.dumps(summary.get("stop_conditions"), indent=2, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--repair3-weights-json", type=Path, default=Path(DEFAULT_REPAIR3_WEIGHTS))
    parser.add_argument("--repair3-runtime-dir", type=Path, default=Path(DEFAULT_REPAIR3_RUNTIME))
    parser.add_argument("--maps", nargs="+", choices=sorted(MAPS), default=list(MAPS))
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instances-per-setting", type=int, default=3)
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--include-static-proxies", action="store_true")
    parser.add_argument("--skip-solver", action="store_true", help="Only summarize an existing --output-jsonl.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve_path(args.binary, root)
    scenario_dir = resolve_path(args.scenario_dir, root)
    output_dir = resolve_path(args.output_dir, root)
    summary_json = resolve_path(args.summary_json, root)
    summary_csv = resolve_path(args.summary_csv, root)
    paired_csv = resolve_path(args.paired_csv, root)
    report = resolve_path(args.report, root)
    repair3_weights = resolve_path(args.repair3_weights_json, root)
    repair3_runtime_dir = resolve_path(args.repair3_runtime_dir, root)
    if None in (binary, scenario_dir, output_dir, summary_json, summary_csv, paired_csv, report, repair3_weights, repair3_runtime_dir):
        raise ValueError("required paths could not be resolved")
    assert binary and scenario_dir and output_dir and summary_json and summary_csv and paired_csv and report
    assert repair3_weights and repair3_runtime_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = resolve_path(args.output_jsonl, root) if args.output_jsonl else _jsonl_name(output_dir)
    assert output_jsonl
    command_log = output_jsonl.with_name(output_jsonl.stem + "_commands.jsonl")
    additive_model = root / "configs/phase5/laur_additive_only"
    repair3_runtime, repair3_status = ensure_repair3_runtime(root, repair3_weights, repair3_runtime_dir)
    methods, skipped_methods = build_methods(
        root=root,
        additive_model=additive_model,
        repair3_runtime=repair3_runtime,
        include_static_proxies=bool(args.include_static_proxies),
    )
    skipped_methods.append({"method": "repair3_runtime_export", "reason": repair3_status})

    if not args.skip_solver:
        if not binary.exists():
            raise FileNotFoundError(f"missing solver binary {binary}")
        if output_jsonl.exists():
            raise FileExistsError(f"output JSONL already exists: {output_jsonl}")
        run_solver_grid(
            root=root,
            binary=binary,
            output_jsonl=output_jsonl,
            command_log=command_log,
            maps=list(args.maps),
            agent_counts=[int(value) for value in args.agent_counts],
            instances_per_setting=int(args.instances_per_setting),
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            scenario_dir=scenario_dir,
            methods=methods,
        )

    raw_rows = _read_jsonl(output_jsonl)
    normalized_rows = [normalize_run_row(row) for row in raw_rows]
    schema_errors: list[str] = []
    for index, row in enumerate(normalized_rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))
    summary_rows = summarize_rows(normalized_rows)
    paired = paired_rows(normalized_rows)
    summary = {
        "schema_version": "phase5p5_laur_diagnostic_preflight_exec_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "raw_jsonl": str(output_jsonl),
        "command_log_jsonl": str(command_log),
        "summary_csv": str(summary_csv),
        "paired_csv": str(paired_csv),
        "schema_errors": schema_errors,
        "scope": {
            "maps": list(args.maps),
            "agent_counts": [int(value) for value in args.agent_counts],
            "instances_per_setting": int(args.instances_per_setting),
            "time_limit_sec": float(args.time_limit_sec),
            "ltm_max_iterations": int(args.ltm_max_iterations),
            "methods": [method.alias for method in methods],
        },
        "skipped_methods": skipped_methods,
        "summary_rows": summary_rows,
        "paired_row_count": len(paired),
        "stop_conditions": stop_condition_snapshot(summary_rows, paired),
    }
    _write_csv(
        summary_csv,
        summary_rows,
        [
            "map",
            "agents",
            "method",
            "runs",
            "successes",
            "success_rate",
            "sum_of_loss_ratio_mean",
            "expanded_nodes_mean",
            "time_to_first_solution_ms_mean",
            "returned_solutions_count_mean",
            "low_level_pibt_calls_mean",
            "laur_overhead_ms_mean",
            "laur_inference_count_mean",
            "laur_additive_fallback_count_mean",
            "laur_safety_disabled_count_mean",
            "fallback_defer_rate",
            "non_additive_update_rate",
            "selected_harmful_update_rate",
            "selected_rules",
        ],
    )
    _write_csv(
        paired_csv,
        paired,
        [
            "map",
            "agents",
            "seed",
            "scen",
            "baseline_method",
            "contender_method",
            "baseline_success",
            "contender_success",
            "baseline_ratio",
            "contender_ratio",
            "delta_ratio",
            "contender_better",
        ],
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"summary_json": str(summary_json), "summary_csv": str(summary_csv), "paired_csv": str(paired_csv), "report": str(report)}))
    return 0 if not schema_errors else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
