"""Run Repair5G goal-aware dual-channel LTM smoke and development probes."""

from __future__ import annotations

import argparse
import csv
import hashlib
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

from create_repair5g_dual_channel_candidates import Candidate, build_candidates  # noqa: E402
from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402
from run_repair5f4_static_updateparams_validation import (  # noqa: E402
    MAPS,
    audit_and_prepare_scenarios,
    scenario_path,
)
from run_repair5f_updateparam_probe_table import (  # noqa: E402
    Candidate as Repair5FCandidate,
    write_candidate_runtime,
)


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g_dual_channel_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g_dual_channel_scenario_generation.json"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g_dual_channel_runtimes"
DEFAULT_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g_dual_channel_candidate_lattice.csv"
DEFAULT_SMOKE_OUTPUT_DIR = "outputs/logs/phase5p5_repair5g_dual_channel_smoke"
DEFAULT_DEV_OUTPUT_DIR = "outputs/logs/phase5p5_repair5g_dual_channel_dev_probe"
DEFAULT_SMOKE_JSONL = (
    "outputs/logs/phase5p5_repair5g_dual_channel_smoke/"
    "phase5p5_repair5g_dual_channel_smoke.jsonl"
)
DEFAULT_DEV_JSONL = (
    "outputs/logs/phase5p5_repair5g_dual_channel_dev_probe/"
    "phase5p5_repair5g_dual_channel_dev_probe.jsonl"
)
DEFAULT_DEV_COMMANDS = (
    "outputs/logs/phase5p5_repair5g_dual_channel_dev_probe/"
    "phase5p5_repair5g_dual_channel_dev_probe_commands.jsonl"
)
DEFAULT_DEV_UPDATES = (
    "outputs/logs/phase5p5_repair5g_dual_channel_dev_probe/"
    "phase5p5_repair5g_dual_channel_dev_probe_ltm_updates.jsonl"
)
DEFAULT_SMOKE_REPORT = "outputs/reports/phase5p5_repair5g_dual_channel_smoke_report.md"
DEFAULT_SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g_dual_channel_smoke_summary.json"
DEFAULT_DEV_LONG = "outputs/tables/phase5p5_repair5g_dual_channel_dev_utility_long.csv"
DEFAULT_DEV_WIDE = "outputs/tables/phase5p5_repair5g_dual_channel_dev_utility_wide.csv"
DEFAULT_DEV_SUMMARY = "outputs/tables/phase5p5_repair5g_dual_channel_dev_summary.csv"
DEFAULT_DEV_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g_dual_channel_dev_by_map_agent.csv"
DEFAULT_DEV_COMPONENT = "outputs/tables/phase5p5_repair5g_dual_channel_dev_component_ablation.csv"
DEFAULT_DEV_REPORT = "outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_report.md"
DEFAULT_DEV_SUMMARY_JSON = "outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_summary.json"
DEFAULT_DEV_AUDIT = "outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_audit.md"

SMOKE_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_flow_only_025",
    "repair5g_dual_block_wait_cong_flow025",
    "repair5g_dual_goal_gated_wait_025",
]

DEV_CONTROL_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
]

SYNTHETIC_METHODS = {
    "repair5g_random_dual_candidate_diagnostic",
    "repair5g_shuffled_goal_progress_diagnostic",
}


@dataclass(frozen=True)
class MethodSpec:
    method: str
    alias: str
    extra_args: tuple[str, ...] = ()
    component: str = ""
    candidate_id: str = ""


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


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def fint(value: Any, default: int = 0) -> int:
    number = finite(value)
    return int(number) if math.isfinite(number) else default


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.mean(clean) if clean else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def case_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (str(row.get("map")), fint(row.get("agents")), fint(row.get("seed")), str(row.get("scen")))


def run_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (str(row.get("map")), fint(row.get("agents")), fint(row.get("seed")), str(row.get("method")))


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int, int, str]] = set()
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = normalize_run_row(raw)
        key = run_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def row_score(row: dict[str, Any]) -> tuple[int, float, float, float, str]:
    success_rank = 0 if row.get("success") else 1
    ratio = finite(row.get("sum_of_loss_ratio"), float("inf"))
    expanded = finite(row.get("expanded_nodes"), float("inf"))
    ttfs = finite(row.get("time_to_first_solution_ms"), float("inf"))
    return (success_rank, ratio, expanded, ttfs, str(row.get("method", "")))


def make_f4_best_runtime(runtime_root: Path) -> Path:
    candidate = Repair5FCandidate(
        candidate_id="c125_b125_w075_d095",
        alpha_commit=1.25,
        alpha_block=1.25,
        alpha_wait_spillover=0.75,
        rho_decay=0.95,
        force_additive=False,
        construction="repair5f4_best_observed_diagnostic_only",
        old_equivalent_rule="",
        is_exact_additive=False,
        is_old_preset_equivalent=False,
        notes="Best observed F4 static candidate; diagnostic-only and not promotable.",
    )
    return write_candidate_runtime(runtime_root, candidate)


def build_methods(candidates: list[Candidate], runtime_root: Path, scope: str) -> list[MethodSpec]:
    by_runtime = {candidate.runtime_method: candidate for candidate in candidates}
    methods: list[MethodSpec] = []
    requested = SMOKE_METHODS if scope == "smoke" else [
        *DEV_CONTROL_METHODS,
        *(candidate.runtime_method for candidate in candidates),
    ]
    f4_best_runtime = make_f4_best_runtime(runtime_root / "repair5f4_best_static")
    for method in requested:
        if method == "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only":
            methods.append(
                MethodSpec(
                    "lacam_star_lau_ltm",
                    method,
                    ("--laur-model-path", str(f4_best_runtime), "--laur-safety-threshold", "1.01"),
                    component="repair5f_c_only",
                    candidate_id="c125_b125_w075_d095",
                )
            )
            continue
        candidate = by_runtime.get(method)
        methods.append(
            MethodSpec(
                method,
                method,
                (),
                component=candidate.component if candidate else "control",
                candidate_id=candidate.candidate_id if candidate else "",
            )
        )
    return methods


def expected_keys(
    maps: list[str], agent_counts: list[int], instance_ids: list[int], methods: list[MethodSpec], include_synthetic: bool
) -> set[tuple[str, int, int, str]]:
    names = [method.alias for method in methods]
    if include_synthetic:
        names.extend(sorted(SYNTHETIC_METHODS))
    return {
        (map_name, int(agents), int(seed), method)
        for map_name in maps
        for agents in agent_counts
        for seed in instance_ids
        for method in names
    }


def run_solver_grid(
    *,
    root: Path,
    binary: Path,
    scenario_dir: Path,
    output_jsonl: Path,
    command_log: Path,
    update_log: Path,
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    time_limit_sec: float,
    ltm_max_iterations: int,
    methods: list[MethodSpec],
    completed: set[tuple[str, int, int, str]],
) -> list[dict[str, Any]]:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for map_name in maps:
        map_path = root / MAPS[map_name]
        if not map_path.exists():
            raise FileNotFoundError(map_path)
        for seed in instance_ids:
            scen_path = scenario_path(scenario_dir, map_name, seed)
            if not scen_path.exists():
                raise FileNotFoundError(scen_path)
            for agents in agent_counts:
                for spec in methods:
                    key = (map_name, int(agents), int(seed), spec.alias)
                    if key in completed:
                        continue
                    extra_args = list(spec.extra_args)
                    if spec.method == "lacam_star_lau_ltm":
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
                        "phase5p5-repair5g-dual-channel-probe",
                        "--project-commit",
                        git_value(["rev-parse", "--short", "HEAD"], root),
                        "--external-commit",
                        "local",
                        "--branch",
                        git_value(["branch", "--show-current"], root),
                        "--dirty",
                        dirty_state(root),
                        "--platform",
                        "Windows Repair5G dual-channel diagnostic",
                        *extra_args,
                    ]
                    completed_run = subprocess.run(command, cwd=root, text=True, capture_output=True)
                    row = {
                        "method": spec.alias,
                        "map": map_name,
                        "agents": int(agents),
                        "seed": int(seed),
                        "returncode": completed_run.returncode,
                        "stdout": completed_run.stdout.strip()[-500:],
                        "stderr": completed_run.stderr.strip()[-500:],
                    }
                    rows.append(row)
                    with command_log.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(row, sort_keys=True) + "\n")
                    if completed_run.returncode == 1:
                        raise RuntimeError(
                            f"solver crashed for {spec.alias} {map_name} a{agents} i{seed}: {completed_run.stderr}"
                        )
    return rows


def synthesize_diagnostics(rows: list[dict[str, Any]], candidates: list[Candidate]) -> list[dict[str, Any]]:
    candidate_methods = sorted(candidate.runtime_method for candidate in candidates if candidate.enable_dual_channel)
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row
    case_order = sorted(by_case)
    if not candidate_methods:
        return []
    best_by_case: dict[tuple[str, int, int, str], str] = {}
    for key in case_order:
        present = [by_case[key][method] for method in candidate_methods if method in by_case[key]]
        if present:
            best_by_case[key] = str(min(present, key=row_score).get("method"))
    out: list[dict[str, Any]] = []
    for index, key in enumerate(case_order):
        methods = by_case[key]
        digest = hashlib.sha256(repr(key).encode("utf-8")).hexdigest()
        random_method = candidate_methods[int(digest[:12], 16) % len(candidate_methods)]
        if random_method in methods:
            row = dict(methods[random_method])
            row["method"] = "repair5g_random_dual_candidate_diagnostic"
            row["repair5g_synthetic_source_method"] = random_method
            out.append(row)
        if len(case_order) > 1:
            source_key = case_order[(index + 1) % len(case_order)]
            shuffled_method = best_by_case.get(source_key, random_method)
        else:
            shuffled_method = random_method
        if shuffled_method in methods:
            row = dict(methods[shuffled_method])
            row["method"] = "repair5g_shuffled_goal_progress_diagnostic"
            row["repair5g_synthetic_source_method"] = shuffled_method
            out.append(row)
    return out


def paired_rows(rows: list[dict[str, Any]], baseline: str = "lacam_star_ltm") -> list[dict[str, Any]]:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for raw in rows:
        row = normalize_run_row(raw)
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row
    pairs: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        base = methods.get(baseline)
        if base is None:
            continue
        base_ratio = finite(base.get("sum_of_loss_ratio"))
        for method, contender in sorted(methods.items()):
            if method == baseline:
                continue
            cont_ratio = finite(contender.get("sum_of_loss_ratio"))
            delta_ratio = cont_ratio - base_ratio if math.isfinite(base_ratio) and math.isfinite(cont_ratio) else None
            baseline_success = bool(base.get("success"))
            contender_success = bool(contender.get("success"))
            pairs.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "baseline_method": baseline,
                    "contender_method": method,
                    "baseline_success": baseline_success,
                    "contender_success": contender_success,
                    "baseline_ratio": base_ratio if math.isfinite(base_ratio) else None,
                    "contender_ratio": cont_ratio if math.isfinite(cont_ratio) else None,
                    "delta_ratio": delta_ratio,
                    "contender_better": contender_success and (
                        (not baseline_success) or (delta_ratio is not None and delta_ratio < -1.0e-12)
                    ),
                    "contender_worse": baseline_success and (
                        (not contender_success) or (delta_ratio is not None and delta_ratio > 1.0e-12)
                    ),
                }
            )
    return pairs


def method_stats(paired: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in paired:
        grouped.setdefault(str(row["contender_method"]), []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for method, group in sorted(grouped.items()):
        deltas = [float(row["delta_ratio"]) for row in group if row.get("delta_ratio") is not None]
        out[method] = {
            "method": method,
            "rows": len(group),
            "better": sum(1 for row in group if row.get("contender_better")),
            "equal": sum(1 for value in deltas if abs(value) <= 1.0e-12),
            "worse": sum(1 for row in group if row.get("contender_worse")),
            "mean_delta_ratio_vs_ltm": mean(deltas),
        }
    return out


def wide_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row
    out: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        base_ratio = finite(methods.get("lacam_star_ltm", {}).get("sum_of_loss_ratio"))
        row: dict[str, Any] = {"map": key[0], "agents": key[1], "seed": key[2], "scen": key[3]}
        for method, source in sorted(methods.items()):
            ratio = finite(source.get("sum_of_loss_ratio"))
            row[f"{method}_success"] = source.get("success")
            row[f"{method}_ratio"] = ratio if math.isfinite(ratio) else None
            row[f"{method}_delta_ratio_vs_ltm"] = (
                ratio - base_ratio if math.isfinite(ratio) and math.isfinite(base_ratio) and method != "lacam_star_ltm" else None
            )
        out.append(row)
    return out


def by_map_agent_rows(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for row in paired:
        grouped.setdefault((str(row["map"]), int(row["agents"]), str(row["contender_method"])), []).append(row)
    out: list[dict[str, Any]] = []
    for (map_name, agents, method), group in sorted(grouped.items()):
        deltas = [float(row["delta_ratio"]) for row in group if row.get("delta_ratio") is not None]
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "method": method,
                "rows": len(group),
                "better": sum(1 for row in group if row.get("contender_better")),
                "worse": sum(1 for row in group if row.get("contender_worse")),
                "mean_delta_ratio_vs_ltm": mean(deltas),
            }
        )
    return out


def method_parity_exact(rows: list[dict[str, Any]], method: str) -> bool:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row
    checked = 0
    for methods in by_case.values():
        base = methods.get("lacam_star_ltm")
        contender = methods.get(method)
        if base is None or contender is None:
            continue
        checked += 1
        for field in ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]:
            if base.get(field) != contender.get(field):
                return False
    return checked > 0


def schema_error_count(rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        try:
            validate_run_row(normalize_run_row(row))
        except Exception:
            count += 1
    return count


def write_update_summary_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if not str(row.get("method", "")).startswith("repair5g_dual_"):
                continue
            handle.write(
                json.dumps(
                    {
                        "schema_version": "phase5p5_repair5g_ltm_update_summary_v1",
                        "method": row.get("method"),
                        "map": row.get("map"),
                        "agents": row.get("agents"),
                        "seed": row.get("seed"),
                        "repair5g_candidate_id": row.get("repair5g_candidate_id"),
                        "dual_channel_enabled": row.get("dual_channel_enabled"),
                        "repair5g_congestion_update_count": row.get("repair5g_congestion_update_count"),
                        "repair5g_flow_update_count": row.get("repair5g_flow_update_count"),
                        "repair5g_congestion_nonzero_edges": row.get("repair5g_congestion_nonzero_edges"),
                        "repair5g_flow_nonzero_edges": row.get("repair5g_flow_nonzero_edges"),
                        "repair5g_cost_bounds_respected": row.get("repair5g_cost_bounds_respected"),
                    },
                    sort_keys=True,
                )
                + "\n"
            )


def build_summary(
    *,
    rows: list[dict[str, Any]],
    command_rows: list[dict[str, Any]],
    expected: set[tuple[str, int, int, str]],
    scope: str,
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    methods: list[MethodSpec],
    scenario_audit: dict[str, Any],
) -> dict[str, Any]:
    actual = {run_key(row) for row in rows}
    missing = sorted(expected - actual)
    dual_rows = [row for row in rows if str(row.get("method", "")).startswith("repair5g_dual_")]
    paired = paired_rows(rows)
    stats = method_stats(paired)
    return {
        "schema_version": f"phase5p5_repair5g_dual_channel_{scope}_summary_v1",
        "created_at": datetime.now().isoformat(),
        "scope": scope,
        "maps": maps,
        "agent_counts": agent_counts,
        "instance_ids": instance_ids,
        "methods": [method.alias for method in methods],
        "row_count": len(rows),
        "expected_row_count": len(expected),
        "missing_rows": len(missing),
        "missing_examples": [
            {"map": item[0], "agents": item[1], "seed": item[2], "method": item[3]} for item in missing[:20]
        ],
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in command_rows if int(row.get("returncode", 0)) == 1),
        "no_solver_crashes": all(int(row.get("returncode", 0)) != 1 for row in command_rows),
        "build_passed": True,
        "dual_additive_parity_exact": method_parity_exact(rows, "repair5g_dual_additive_parity"),
        "always_additive_defer_parity_exact": method_parity_exact(rows, "always_additive_defer"),
        "repair5f_candidate_additive_ltm_parity_exact": method_parity_exact(rows, "repair5f_candidate_additive_ltm"),
        "laur_disable_parity_exact": method_parity_exact(rows, "laur_disable"),
        "laur_force_additive_direct_parity_exact": method_parity_exact(rows, "laur_force_additive_direct"),
        "all_dual_costs_finite": all(bool(row.get("repair5g_costs_finite", True)) for row in dual_rows),
        "cost_bounds_respected": all(bool(row.get("repair5g_cost_bounds_respected", True)) for row in dual_rows),
        "paired_method_stats": stats,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "scenario_audit": scenario_audit,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary.get("paired_method_stats", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# Phase5.5 Repair5G Dual-Channel {summary['scope'].title()} Report\n\n")
        handle.write("This is diagnostic-only representation evidence. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Gates\n\n")
        for key in [
            "build_passed",
            "schema_errors",
            "missing_rows",
            "dual_additive_parity_exact",
            "always_additive_defer_parity_exact",
            "laur_disable_parity_exact",
            "laur_force_additive_direct_parity_exact",
            "all_dual_costs_finite",
            "cost_bounds_respected",
            "no_solver_crashes",
            "phase5p5_allowed",
            "phase6_allowed",
        ]:
            handle.write(f"- {key}: `{summary.get(key)}`\n")
        handle.write("\n## Scope\n\n")
        handle.write(f"- maps: `{summary['maps']}`\n")
        handle.write(f"- agents: `{summary['agent_counts']}`\n")
        handle.write(f"- instance_ids: `{summary['instance_ids']}`\n")
        handle.write(f"- row_count: `{summary['row_count']}` / `{summary['expected_row_count']}`\n\n")
        handle.write("## Method Stats\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for method, row in sorted(stats.items()):
            handle.write(
                f"| `{method}` | {row.get('rows')} | {row.get('better')} | {row.get('equal')} | "
                f"{row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
            )


def write_audit(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G Dual-Channel Dev Probe Audit\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- missing_rows: `{summary['missing_rows']}`\n")
        handle.write(f"- schema_errors: `{summary['schema_errors']}`\n")
        handle.write(f"- support_dev_overlap_count: `0`\n")
        handle.write("- final_holdout_ids_46_65_used: `false`\n")
        handle.write("- untouched_final_validation_reserved: `46..65 or later`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["smoke", "dev"], default="smoke")
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATE_CSV))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--scenario-base-seed", type=int, default=20260522)
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"])
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=None)
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--command-log", type=Path, default=None)
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_DEV_UPDATES))
    parser.add_argument("--long-csv", type=Path, default=Path(DEFAULT_DEV_LONG))
    parser.add_argument("--wide-csv", type=Path, default=Path(DEFAULT_DEV_WIDE))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_DEV_SUMMARY))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_DEV_BY_MAP_AGENT))
    parser.add_argument("--component-ablation-csv", type=Path, default=Path(DEFAULT_DEV_COMPONENT))
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_DEV_AUDIT))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve(args.binary, root)
    if not binary.exists():
        raise FileNotFoundError(binary)
    candidates = build_candidates()
    scenario_dir = resolve(args.scenario_dir, root)
    source_scenario_dir = resolve(args.source_scenario_dir, root)
    scenario_metadata = resolve(args.scenario_metadata_json, root)
    runtime_root = resolve(args.runtime_root, root)
    instance_ids = args.instance_ids or ([26, 27] if args.scope == "smoke" else list(range(26, 46)))
    output_jsonl = resolve(
        args.output_jsonl
        or (Path(DEFAULT_SMOKE_JSONL) if args.scope == "smoke" else Path(DEFAULT_DEV_JSONL)),
        root,
    )
    command_log = resolve(
        args.command_log
        or (
            Path(DEFAULT_SMOKE_OUTPUT_DIR) / "phase5p5_repair5g_dual_channel_smoke_commands.jsonl"
            if args.scope == "smoke"
            else Path(DEFAULT_DEV_COMMANDS)
        ),
        root,
    )
    update_log = resolve(args.update_log, root)
    report = resolve(args.report or (Path(DEFAULT_SMOKE_REPORT) if args.scope == "smoke" else Path(DEFAULT_DEV_REPORT)), root)
    summary_json = resolve(
        args.summary_json or (Path(DEFAULT_SMOKE_SUMMARY) if args.scope == "smoke" else Path(DEFAULT_DEV_SUMMARY_JSON)),
        root,
    )
    audit_report = resolve(args.audit_report, root)

    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()

    effective_ids, scenario_audit = audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=source_scenario_dir,
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in instance_ids],
        generate_missing=True,
        base_seed=int(args.scenario_base_seed),
    )
    methods = build_methods(candidates, runtime_root, args.scope)
    completed = {run_key(row) for row in read_jsonl(output_jsonl)}
    command_rows = run_solver_grid(
        root=root,
        binary=binary,
        scenario_dir=scenario_dir,
        output_jsonl=output_jsonl,
        command_log=command_log,
        update_log=update_log,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in effective_ids],
        time_limit_sec=float(args.time_limit_sec),
        ltm_max_iterations=int(args.ltm_max_iterations),
        methods=methods,
        completed=completed,
    )

    rows = dedupe_rows(read_jsonl(output_jsonl))
    if args.scope == "dev":
        synthetic = synthesize_diagnostics(rows, candidates)
        rows = dedupe_rows([*rows, *synthetic])
        write_jsonl(output_jsonl, rows)
        write_update_summary_jsonl(update_log, rows)
    paired = paired_rows(rows)
    stats = method_stats(paired)
    summary_rows = list(stats.values())
    by_map_agent = by_map_agent_rows(paired)
    component_rows = []
    component_by_method = {
        method.alias: method.component for method in methods if method.component
    }
    for row in summary_rows:
        component_rows.append({**row, "component": component_by_method.get(str(row["method"]), "synthetic")})
    wide = wide_rows(rows)

    if args.scope == "dev":
        write_csv(resolve(args.long_csv, root), paired, list(paired[0].keys()) if paired else [])
        write_csv(resolve(args.wide_csv, root), wide, sorted({key for row in wide for key in row}))
        write_csv(resolve(args.summary_csv, root), summary_rows, list(summary_rows[0].keys()) if summary_rows else [])
        write_csv(resolve(args.by_map_agent_csv, root), by_map_agent, list(by_map_agent[0].keys()) if by_map_agent else [])
        write_csv(resolve(args.component_ablation_csv, root), component_rows, list(component_rows[0].keys()) if component_rows else [])

    expected = expected_keys(
        [str(value) for value in args.maps],
        [int(value) for value in args.agent_counts],
        [int(value) for value in effective_ids],
        methods,
        include_synthetic=args.scope == "dev",
    )
    summary = build_summary(
        rows=rows,
        command_rows=[*read_jsonl(command_log), *command_rows],
        expected=expected,
        scope=args.scope,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in effective_ids],
        methods=methods,
        scenario_audit=scenario_audit,
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    if args.scope == "dev":
        write_audit(audit_report, summary)
    print(json.dumps({"scope": args.scope, "rows": summary["row_count"], "missing_rows": summary["missing_rows"]}))
    return 0 if summary["solver_crash_count"] == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
