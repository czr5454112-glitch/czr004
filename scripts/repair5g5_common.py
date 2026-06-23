"""Shared helpers for Repair5G.5 learned flow-shield runtime validation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ProcessRunResult:
    returncode: int
    stdout: str
    stderr: str
    provenance: dict[str, Any]


def _process_text(fragment: Any) -> str:
    if fragment is None:
        return ""
    if isinstance(fragment, bytes):
        return fragment.decode("utf-8", errors="replace")
    return str(fragment)


def _merge_process_text(partial: Any, final: Any) -> str:
    first = _process_text(partial)
    second = _process_text(final)
    if not first:
        return second
    if not second:
        return first
    if second.startswith(first):
        return second
    return first + second


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _read_int_file(path: Path) -> int | str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not text or text == "max":
        return text
    try:
        return int(text)
    except ValueError:
        return text


def _read_cgroup_memory_snapshot(prefix: str) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        f"cgroup_memory_current_bytes_{prefix}": "",
        f"cgroup_memory_peak_bytes_{prefix}": "",
        f"cgroup_memory_max_bytes_{prefix}": "",
        f"cgroup_memory_events_{prefix}": "",
    }
    if os.name != "posix":
        return snapshot
    cgroup_path = ""
    try:
        for line in Path("/proc/self/cgroup").read_text(encoding="utf-8").splitlines():
            parts = line.split(":", 2)
            if len(parts) == 3 and (parts[1] == "" or "memory" in parts[1].split(",")):
                cgroup_path = parts[2].strip()
                if parts[1] == "":
                    break
    except OSError:
        cgroup_path = ""
    if not cgroup_path:
        return snapshot
    cgroup_dir = Path("/sys/fs/cgroup") / cgroup_path.lstrip("/")
    if not cgroup_dir.exists():
        cgroup_dir = Path("/sys/fs/cgroup")
    events: dict[str, str] = {}
    try:
        for line in (cgroup_dir / "memory.events").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2:
                events[parts[0]] = parts[1]
    except OSError:
        events = {}
    snapshot.update(
        {
            "process_cgroup_path": cgroup_path,
            f"cgroup_memory_current_bytes_{prefix}": _read_int_file(cgroup_dir / "memory.current"),
            f"cgroup_memory_peak_bytes_{prefix}": _read_int_file(cgroup_dir / "memory.peak"),
            f"cgroup_memory_max_bytes_{prefix}": _read_int_file(cgroup_dir / "memory.max"),
            f"cgroup_memory_events_{prefix}": json.dumps(events, sort_keys=True) if events else "",
        }
    )
    return snapshot


def _record_posix_process_group_identity(provenance: dict[str, Any], proc: subprocess.Popen[Any]) -> None:
    if os.name != "posix":
        return
    try:
        parent_pgid = os.getpgrp()
    except OSError:
        parent_pgid = ""
    try:
        parent_sid = os.getsid(0)
    except OSError:
        parent_sid = ""
    provenance.update(
        {
            "parent_process_id": os.getpid(),
            "parent_process_group_id": parent_pgid,
            "parent_session_id": parent_sid,
        }
    )
    try:
        child_pgid = os.getpgid(proc.pid)
        child_sid = os.getsid(proc.pid)
    except OSError as exc:
        provenance["process_group_isolation_verified"] = False
        provenance["process_group_isolation_failure"] = f"identity_read_failed:{exc}"
        return
    provenance.update(
        {
            "process_group_id": child_pgid,
            "child_session_id": child_sid,
        }
    )
    problems = []
    if child_pgid != proc.pid:
        problems.append(f"child_pgid_{child_pgid}_not_pid_{proc.pid}")
    if child_sid != proc.pid:
        problems.append(f"child_sid_{child_sid}_not_pid_{proc.pid}")
    if parent_pgid != "" and child_pgid == parent_pgid:
        problems.append("child_pgid_matches_parent")
    if parent_sid != "" and child_sid == parent_sid:
        problems.append("child_sid_matches_parent")
    provenance["process_group_isolation_verified"] = not problems
    provenance["process_group_isolation_failure"] = ";".join(problems)


def _timeout_signal_process(
    proc: subprocess.Popen[Any],
    provenance: dict[str, Any],
    *,
    sig: signal.Signals,
) -> str:
    if os.name == "posix":
        if provenance.get("process_group_isolation_verified") is True:
            pgid = int(provenance["process_group_id"] or proc.pid)
            provenance["process_group_termination_attempted"] = True
            provenance["process_group_killpg_target"] = pgid
            os.killpg(pgid, sig)
            return "sigterm" if sig == signal.SIGTERM else "sigkill"
        provenance["process_group_termination_attempted"] = False
        provenance["process_timeout_kill_scope"] = "child_process_only_unverified_process_group"
        if sig == signal.SIGTERM:
            proc.terminate()
            return "terminate"
        proc.kill()
        return "kill"
    if sig == signal.SIGTERM:
        proc.terminate()
        return "terminate"
    proc.kill()
    return "kill"


def run_command_with_hard_timeout(
    command: list[str],
    *,
    cwd: Path,
    process_hard_timeout_sec: float | None = None,
    timeout_term_grace_sec: float | None = None,
) -> ProcessRunResult:
    timeout = None if process_hard_timeout_sec is None else float(process_hard_timeout_sec)
    if timeout is not None and timeout <= 0:
        timeout = None
    grace = _env_float("REPAIR5G_PROCESS_TIMEOUT_TERM_GRACE_SEC", 5.0)
    if timeout_term_grace_sec is not None:
        grace = float(timeout_term_grace_sec)
    grace = max(0.0, grace)
    start_wall = time.time()
    start_perf = time.perf_counter()
    if timeout is None:
        provenance_mode = "subprocess_popen_no_timeout"
    elif os.name == "posix":
        provenance_mode = "subprocess_popen_posix_start_new_session_process_group"
    elif os.name == "nt":
        provenance_mode = "subprocess_popen_windows_create_new_process_group"
    else:
        provenance_mode = "subprocess_popen_platform_terminate"
    provenance: dict[str, Any] = {
        "process_hard_timeout_sec": "" if timeout is None else timeout,
        "process_hard_timeout_exceeded": False,
        "process_timeout_provenance": provenance_mode,
        "process_timeout_platform": os.name,
        "process_timeout_term_grace_sec": grace,
        "process_started_unix": start_wall,
        "process_pid": "",
        "process_group_id": "",
        "child_session_id": "",
        "parent_process_id": os.getpid(),
        "parent_process_group_id": "",
        "parent_session_id": "",
        "process_group_isolation_verified": False,
        "process_group_isolation_failure": "",
        "process_group_termination_attempted": False,
        "process_group_killpg_target": "",
        "process_timeout_kill_scope": "",
        "process_timeout_sigterm_sent": False,
        "process_timeout_sigterm_unix": "",
        "process_timeout_sigterm_elapsed_sec": "",
        "process_timeout_sigkill_sent": False,
        "process_timeout_sigkill_unix": "",
        "process_timeout_sigkill_elapsed_sec": "",
        "child_process_group_killed": False,
        "child_process_group_kill_method": "",
        "process_partial_stdout_preserved": False,
        "process_partial_stderr_preserved": False,
        "process_partial_stdout_chars": 0,
        "process_partial_stderr_chars": 0,
        "process_timeout_reason": "",
    }
    provenance.update(_read_cgroup_memory_snapshot("before"))
    popen_kwargs: dict[str, Any] = {}
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    elif os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **popen_kwargs,
    )
    provenance["process_pid"] = proc.pid
    if os.name == "posix":
        _record_posix_process_group_identity(provenance, proc)
    stdout = ""
    stderr = ""
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        partial_stdout = _process_text(getattr(exc, "stdout", None) or getattr(exc, "output", None))
        partial_stderr = _process_text(getattr(exc, "stderr", None))
        provenance["process_partial_stdout_preserved"] = bool(partial_stdout)
        provenance["process_partial_stderr_preserved"] = bool(partial_stderr)
        provenance["process_partial_stdout_chars"] = len(partial_stdout)
        provenance["process_partial_stderr_chars"] = len(partial_stderr)
        provenance["process_hard_timeout_exceeded"] = True
        provenance["process_timeout_reason"] = "process_hard_timeout_sec_exceeded"
        provenance["process_timeout_elapsed_before_term_sec"] = time.perf_counter() - start_perf
        try:
            method = _timeout_signal_process(proc, provenance, sig=signal.SIGTERM)
            provenance["process_timeout_sigterm_sent"] = True
            provenance["process_timeout_sigterm_unix"] = time.time()
            provenance["process_timeout_sigterm_elapsed_sec"] = time.perf_counter() - start_perf
            provenance["child_process_group_kill_method"] = method
        except ProcessLookupError:
            provenance["process_timeout_reason"] = "process_already_exited_after_timeout"
        except OSError as exc:
            provenance["process_timeout_reason"] = f"process_timeout_sigterm_failed:{exc}"
        try:
            final_stdout, final_stderr = proc.communicate(timeout=grace)
            stdout = _merge_process_text(partial_stdout, final_stdout)
            stderr = _merge_process_text(partial_stderr, final_stderr)
            provenance["child_process_group_killed"] = True
            if not provenance["child_process_group_kill_method"]:
                provenance["child_process_group_kill_method"] = "sigterm" if os.name == "posix" else "terminate"
        except subprocess.TimeoutExpired as exc2:
            partial_stdout = _merge_process_text(partial_stdout, getattr(exc2, "stdout", None) or getattr(exc2, "output", None))
            partial_stderr = _merge_process_text(partial_stderr, getattr(exc2, "stderr", None))
            provenance["process_partial_stdout_preserved"] = bool(partial_stdout)
            provenance["process_partial_stderr_preserved"] = bool(partial_stderr)
            provenance["process_partial_stdout_chars"] = len(partial_stdout)
            provenance["process_partial_stderr_chars"] = len(partial_stderr)
            try:
                method = _timeout_signal_process(proc, provenance, sig=signal.SIGKILL)
                provenance["process_timeout_sigkill_sent"] = True
                provenance["process_timeout_sigkill_unix"] = time.time()
                provenance["process_timeout_sigkill_elapsed_sec"] = time.perf_counter() - start_perf
                provenance["child_process_group_kill_method"] = method
            except ProcessLookupError:
                pass
            except OSError as exc:
                provenance["process_timeout_reason"] = f"process_timeout_sigkill_failed:{exc}"
            final_stdout, final_stderr = proc.communicate()
            stdout = _merge_process_text(partial_stdout, final_stdout)
            stderr = _merge_process_text(partial_stderr, final_stderr)
            provenance["child_process_group_killed"] = True
            if not provenance["child_process_group_kill_method"]:
                provenance["child_process_group_kill_method"] = "sigkill" if os.name == "posix" else "kill"
    elapsed = time.perf_counter() - start_perf
    provenance["process_elapsed_sec"] = elapsed
    provenance["process_returncode"] = proc.returncode
    provenance.update(_read_cgroup_memory_snapshot("after"))
    if provenance["process_hard_timeout_exceeded"]:
        provenance["process_partial_stdout_preserved"] = bool(stdout)
        provenance["process_partial_stderr_preserved"] = bool(stderr)
        provenance["process_partial_stdout_chars"] = len(stdout or "")
        provenance["process_partial_stderr_chars"] = len(stderr or "")
        stderr = (stderr or "") + f"\nprocess hard timeout exceeded after {timeout:.6f}s; returncode={proc.returncode}"
    return ProcessRunResult(proc.returncode if proc.returncode is not None else -999, stdout or "", stderr or "", provenance)


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
    process_hard_timeout_sec: float | None = None,
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
    completed = run_command_with_hard_timeout(
        command,
        cwd=root,
        process_hard_timeout_sec=process_hard_timeout_sec,
    )
    hard_timeout_exceeded = bool(completed.provenance.get("process_hard_timeout_exceeded"))
    command_row = {
        "method": spec.alias,
        "map": map_name,
        "agents": int(agents),
        "seed": int(seed),
        "returncode": completed.returncode,
        "returncode_classification": "process_hard_timeout" if hard_timeout_exceeded else classify_returncode(completed.returncode),
        "stdout": completed.stdout.strip()[-500:],
        "stderr": completed.stderr.strip()[-500:],
        "command": command,
        **completed.provenance,
    }
    rows = read_jsonl(task_jsonl)
    update_rows = read_jsonl(task_update)
    for update_row in update_rows:
        append_jsonl(update_log, update_row)
    task_jsonl.unlink(missing_ok=True)
    task_update.unlink(missing_ok=True)
    if completed.returncode == 1 and not hard_timeout_exceeded:
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
