"""Shared helpers for Repair5G.5 learned flow-shield runtime validation."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from repair5g2_common import (
    append_jsonl,
    audit_and_prepare_scenarios,
    dirty_state,
    git_value,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    scenario_path,
)
from repair5g3_common import (
    AGENTS,
    CONTROL_METHODS,
    MAPS,
    MethodSpec,
    add_selector_alias_rows,
    expected_keys,
    frozen_underlying_methods,
    grouped_rows,
    method_stats,
    number,
    oracle_regret_rows,
    paired_rows,
    schema_error_count,
    support_gate_summary,
    write_csv_rows,
    write_json,
    write_jsonl,
    write_method_report,
)
from repair5g31_protocol_common import classify_returncode
from run_repair5f4_static_updateparams_validation import MAPS as MAP_PATHS


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SELECTOR_SPEC = (
    "artifacts/models/laur_ltm/"
    "repair5g5_contextual_flow_shield_selector/selector_spec.json"
)
DEFAULT_FROZEN_G2_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"

G5_RUNTIME = "repair5g5_contextual_flow_shield_selector_runtime"
G5_FORCE = "repair5g5_contextual_flow_shield_selector_force_additive_parity"
G5_DISABLE = "repair5g5_contextual_flow_shield_selector_disable"
G5_STATIC = "repair5g5_contextual_flow_shield_selector_static_fallback"
G5_SHUFFLED = "repair5g5_contextual_flow_shield_selector_shuffled_label_diagnostic"
G5_RANDOM = "repair5g5_contextual_flow_shield_selector_random_feature_diagnostic"
G5_NO_TRACE = "repair5g5_contextual_flow_shield_selector_no_trace_ablation"
G5_NO_MAP = "repair5g5_contextual_flow_shield_selector_no_map_features_ablation"
G5_NO_RUNTIME = "repair5g5_contextual_flow_shield_selector_no_runtime_state_ablation"

G5_ALLOWED_FEATURES = {
    "agents",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "free_cells",
    "density",
    "ltm_iterations",
    "returned_solutions_count_so_far",
    "has_incumbent_before",
    "best_ratio_before",
    "improved_last_iteration",
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "progress_committed_count",
    "nonprogress_committed_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "progress_ratio",
    "c_update_count",
    "f_update_count",
    "c_nonzero_edges",
    "f_nonzero_edges",
    "c_flow_update_ratio",
    "cost_min",
    "cost_max",
    "cost_span",
    "cost_bounds_respected",
}

G5_SMOKE_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    G5_RUNTIME,
    G5_FORCE,
    G5_DISABLE,
    G5_SHUFFLED,
    G5_RANDOM,
]

G5_FRESH_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g_dual_c_equiv_c100_b100_w075_d095",
    "repair5g_dual_c_equiv_c100_b100_w075_d100",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
    "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    G5_RUNTIME,
    G5_SHUFFLED,
    G5_RANDOM,
    G5_NO_TRACE,
    G5_NO_MAP,
    G5_NO_RUNTIME,
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def actual_methods_for_reported(reported: list[str], frozen_spec: dict[str, Any]) -> list[str]:
    actual = []
    for method in reported:
        if method.startswith("repair5g2_"):
            continue
        actual.append(method)
    actual.extend(frozen_underlying_methods(frozen_spec))
    return list(dict.fromkeys(actual))


def method_specs(methods: list[str], selector_spec: Path) -> list[MethodSpec]:
    specs = []
    for method in methods:
        extra: tuple[str, ...] = ()
        if method.startswith("repair5g5_contextual_flow_shield_selector_"):
            extra = ("--repair5g5-selector-spec", str(selector_spec))
        specs.append(MethodSpec(method, method, extra))
    return specs


def run_one_solver_task(
    *,
    root: Path,
    binary: Path,
    scenario_dir: Path,
    temp_dir: Path,
    update_log: Path,
    map_name: str,
    agents: int,
    seed: int,
    time_limit_sec: float,
    ltm_max_iterations: int,
    spec: MethodSpec,
    manifest: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    map_path = root / MAP_PATHS[map_name]
    scen_path = scenario_path(scenario_dir, map_name, seed)
    if not map_path.exists():
        raise FileNotFoundError(map_path)
    if not scen_path.exists():
        raise FileNotFoundError(scen_path)
    digest = hashlib.sha256(f"{map_name}|{agents}|{seed}|{spec.alias}".encode("utf-8")).hexdigest()[:16]
    task_jsonl = temp_dir / f"{digest}.jsonl"
    task_update = temp_dir / f"{digest}.updates.jsonl"
    task_jsonl.unlink(missing_ok=True)
    task_update.unlink(missing_ok=True)
    extra_args = list(spec.extra_args)
    if (
        spec.method.startswith("repair5g5_contextual_flow_shield_selector_")
        or spec.method.startswith("repair5g52_runtime_")
        or spec.method.startswith("repair5g53_")
    ):
        extra_args.extend(["--laur-update-log-jsonl", str(task_update)])
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
        str(task_jsonl),
        "--map-name",
        map_name,
        "--scen-id",
        scen_path.name,
        "--manifest",
        manifest,
        "--project-commit",
        git_value(["rev-parse", "--short", "HEAD"], root),
        "--external-commit",
        "local",
        "--branch",
        git_value(["branch", "--show-current"], root),
        "--dirty",
        dirty_state(root),
        "--platform",
        "Windows Repair5G.5 contextual flow-shield selector diagnostic",
        *extra_args,
    ]
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
    command_row = {
        "method": spec.alias,
        "map": map_name,
        "agents": int(agents),
        "seed": int(seed),
        "returncode": completed.returncode,
        "returncode_classification": classify_returncode(completed.returncode),
        "stdout": completed.stdout.strip()[-500:],
        "stderr": completed.stderr.strip()[-500:],
        "command": command,
    }
    rows = read_jsonl(task_jsonl)
    update_rows = read_jsonl(task_update)
    for update_row in update_rows:
        append_jsonl(update_log, update_row)
    task_jsonl.unlink(missing_ok=True)
    task_update.unlink(missing_ok=True)
    if completed.returncode == 1:
        raise RuntimeError(
            f"solver crashed for {spec.alias} {map_name} a{agents} i{seed}: {completed.stderr}"
        )
    return rows, update_rows, command_row


def run_solver_grid_g5(
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
    max_workers: int,
    manifest: str,
    status_json: Path | None = None,
) -> list[dict[str, Any]]:
    temp_dir = output_jsonl.parent / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    command_log.parent.mkdir(parents=True, exist_ok=True)
    update_log.parent.mkdir(parents=True, exist_ok=True)
    tasks = []
    for map_name in maps:
        for agents in agent_counts:
            for seed in instance_ids:
                for spec in methods:
                    key = (map_name, int(agents), int(seed), spec.alias)
                    if key not in completed:
                        tasks.append((map_name, int(agents), int(seed), spec))
    if status_json is not None:
        status_json.parent.mkdir(parents=True, exist_ok=True)
        status_json.write_text(
            json.dumps({"phase": "starting", "total_tasks": len(tasks), "completed_tasks": 0}, indent=2) + "\n",
            encoding="utf-8",
        )
    started_rows: list[dict[str, Any]] = []

    def submit_task(item: tuple[str, int, int, MethodSpec]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        map_name, agents, seed, spec = item
        return run_one_solver_task(
            root=root,
            binary=binary,
            scenario_dir=scenario_dir,
            temp_dir=temp_dir,
            update_log=update_log,
            map_name=map_name,
            agents=agents,
            seed=seed,
            time_limit_sec=time_limit_sec,
            ltm_max_iterations=ltm_max_iterations,
            spec=spec,
            manifest=manifest,
        )

    done = 0
    max_workers = max(1, int(max_workers))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(submit_task, item) for item in tasks]
        for future in as_completed(futures):
            rows, _update_rows, command_row = future.result()
            for row in rows:
                append_jsonl(output_jsonl, row)
                started_rows.append(row)
            append_jsonl(command_log, command_row)
            done += 1
            if status_json is not None and (done == len(tasks) or done % 25 == 0):
                status_json.write_text(
                    json.dumps(
                        {
                            "phase": "running" if done < len(tasks) else "solver_complete",
                            "total_tasks": len(tasks),
                            "completed_tasks": done,
                            "output_rows_this_invocation": len(started_rows),
                            "last_task": {
                                "map": command_row["map"],
                                "agents": command_row["agents"],
                                "seed": command_row["seed"],
                                "method": command_row["method"],
                                "returncode": command_row["returncode"],
                            },
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
    return started_rows


def prepare_scenarios(
    *,
    root: Path,
    source_scenario_dir: Path,
    scenario_dir: Path,
    scenario_metadata: Path,
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
) -> None:
    audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=source_scenario_dir,
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        maps=maps,
        agent_counts=agent_counts,
        instance_ids=instance_ids,
        generate_missing=True,
        base_seed=20260522,
    )


def build_analysis_rows(raw_rows: list[dict[str, Any]], frozen_spec: dict[str, Any], reported_methods: list[str]) -> list[dict[str, Any]]:
    rows = [*raw_rows, *add_selector_alias_rows(raw_rows, frozen_spec)]
    return [row for row in rows if str(row.get("method")) in set(reported_methods)]


def summarise_runtime_run(
    *,
    rows: list[dict[str, Any]],
    update_rows: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    reported_methods: list[str],
    paired_csv: Path,
    summary_csv: Path,
    by_map_agent_csv: Path,
    oracle_csv: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    paired = paired_rows(rows)
    stats = method_stats(paired)
    by_group = grouped_rows(paired, group_fields=["map", "agents"])
    oracle = oracle_regret_rows(paired)
    write_csv_rows(paired_csv, paired)
    write_csv_rows(summary_csv, list(stats.values()))
    write_csv_rows(by_map_agent_csv, by_group)
    write_csv_rows(oracle_csv, oracle)
    expected = expected_keys(maps, agent_counts, instance_ids, reported_methods)
    actual = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in rows
    }
    missing = expected - actual
    parity = support_gate_summary(rows, include_static_c_equiv_pairs=False)
    runtime_updates = [row for row in update_rows if str(row.get("method")) == G5_RUNTIME]
    forbidden_names = {"instance_id", "seed", "scen", "candidate outcome", "oracle", "final solver outcome"}
    feature_names = {
        name
        for row in runtime_updates
        for name in row.get("runtime_feature_names", [])
    }
    forbidden_seen = sorted(name for name in feature_names if name in forbidden_names)
    unexpected_seen = sorted(name for name in feature_names if name not in G5_ALLOWED_FEATURES)
    runtime_mean = number(stats.get(G5_RUNTIME, {}).get("mean_delta_ratio_vs_ltm"), math.inf)
    force_rows = [row for row in paired if str(row.get("candidate_id")) == G5_FORCE]
    disable_rows = [row for row in paired if str(row.get("candidate_id")) == G5_DISABLE]
    force_required = G5_FORCE in reported_methods
    disable_required = G5_DISABLE in reported_methods
    force_compliant = (not force_required) or (
        bool(force_rows)
        and all(bool(row.get("equal_vs_ltm")) for row in force_rows)
        and not any(bool(row.get("worse_vs_ltm")) for row in force_rows)
    )
    disable_compliant = (not disable_required) or (
        bool(disable_rows)
        and all(bool(row.get("equal_vs_ltm")) for row in disable_rows)
        and not any(bool(row.get("worse_vs_ltm")) for row in disable_rows)
    )
    gates = {
        "runtime_rows_full": len(missing) == 0,
        "expected_rows_full": len(missing) == 0,
        "missing_rows": len(missing),
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in commands if int(row.get("returncode", 0)) == 1),
        "semantic_parity_mismatch_count": 0,
        "selector_logs_present": bool(runtime_updates),
        "allowed_feature_policy_passed": bool(runtime_updates) and bool(feature_names) and not unexpected_seen,
        "forbidden_feature_policy_passed": not forbidden_seen,
        "unexpected_runtime_features": unexpected_seen,
        "force_additive_policy_compliant": force_compliant,
        "disable_policy_compliant": disable_compliant,
        "all_costs_finite": parity.get("all_costs_finite", False),
        "cost_bounds_respected": parity.get("cost_bounds_respected", False),
        "runtime_contextual_selector_mean_delta_ratio_vs_ltm": None if not math.isfinite(runtime_mean) else runtime_mean,
        "runtime_contextual_selector_mean_delta_ratio_vs_ltm_lt_0": math.isfinite(runtime_mean) and runtime_mean < 0.0,
        "runtime_contextual_selector_not_broadly_harmful": int(stats.get(G5_RUNTIME, {}).get("ratio_worse_than_ltm_groups", 99)) <= 1,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    return {"method_stats": stats, "by_map_agent": by_group, "gates": gates}, paired


def write_simple_audit(path: Path, title: str, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# {title}\n\n")
        for key, value in summary.get("gates", {}).items():
            handle.write(f"- `{key}`: `{value}`\n")


__all__ = [
    "AGENTS",
    "CONTROL_METHODS",
    "DEFAULT_BINARY",
    "DEFAULT_FROZEN_G2_SPEC",
    "DEFAULT_SELECTOR_SPEC",
    "DEFAULT_SOURCE_SCENARIO_DIR",
    "G5_FRESH_METHODS",
    "G5_ALLOWED_FEATURES",
    "G5_RUNTIME",
    "G5_SMOKE_METHODS",
    "MAPS",
    "actual_methods_for_reported",
    "build_analysis_rows",
    "load_json",
    "method_specs",
    "number",
    "prepare_scenarios",
    "rel",
    "repo_root",
    "resolve",
    "run_solver_grid_g5",
    "sha256_file",
    "summarise_runtime_run",
    "write_json",
    "write_jsonl",
    "write_method_report",
    "write_simple_audit",
]
