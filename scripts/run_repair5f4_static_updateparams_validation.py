"""Run Repair5F.4-A fresh-ID validation for locked static UpdateParams.

The locked main rule is c100_b100_w075_d090. This runner audits freshness,
generates missing fresh scenarios with the existing deterministic Phase1a
scenario policy, runs the closed-loop solver grid, and writes the paired tables,
summary statistics, component ablations, and leakage/parity audits required by
the F4 plan. It never retunes the locked rule and never grants Phase5.5 or
Phase6 permission.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402
from generate_phase1a_scenarios import (  # noqa: E402
    SCRIPT_VERSION as SCENARIO_GENERATOR_VERSION,
    deranged_goals,
    largest_component,
    map_seed,
    read_map,
    scenario_text,
)
from run_repair5f_updateparam_probe_table import (  # noqa: E402
    Candidate,
    read_candidates,
    write_candidate_runtime,
)


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5f4_static_updateparams_validation_scenarios"
DEFAULT_SCENARIO_METADATA = (
    "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_scenario_generation.json"
)
DEFAULT_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5f_candidate_lattice.csv"
DEFAULT_SELECTOR_RUNTIME = "artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector"
DEFAULT_E5_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker"
DEFAULT_E5_SHUFFLED_RUNTIME = (
    "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic"
)
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5f4_static_updateparams_validation_runtimes"
DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5f4_static_updateparams_validation"
DEFAULT_OUTPUT_JSONL = (
    "outputs/logs/phase5p5_repair5f4_static_updateparams_validation/"
    "phase5p5_repair5f4_static_updateparams_validation.jsonl"
)
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_summary.csv"
DEFAULT_BY_MAP_AGENT = (
    "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_by_map_agent.csv"
)
DEFAULT_COMPONENT_ABLATION = (
    "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_component_ablation.csv"
)
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_report.md"
DEFAULT_SUMMARY_JSON = (
    "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_summary.json"
)
DEFAULT_AUDIT_REPORT = "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_audit.md"
DEFAULT_FRESHNESS_AUDIT = (
    "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_freshness_audit.md"
)
DEFAULT_FRESHNESS_AUDIT_JSON = (
    "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_freshness_audit_summary.json"
)
DEFAULT_DECISION = "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_decision.md"

MAPS = {
    "random-32-32-20": "external/lacam2/scripts/map/random-32-32-20.map",
    "maze-32-32-4": "external/lacam2/scripts/map/maze-32-32-4.map",
    "warehouse-10-20-10-2-1": "external/lacam2/scripts/map/warehouse-10-20-10-2-1.map",
}

LOCKED_MAIN_CANDIDATE = "c100_b100_w075_d090"
SUPPORT_IDS = set(range(1, 21))
F2F3_HOLDOUT_IDS = set(range(21, 26))

BASE_METHOD = "lacam_star_ltm"
STATIC_PREFIX = "repair5f_static_"
DETERMINISTIC_RANDOM_METHOD = "repair5f_f4_deterministic_random_candidate_diagnostic"

COMPONENT_ABLATIONS = {
    "repair5f_static_c100_b100_w075_d100": "wait-spillover reduction only",
    "repair5f_static_c100_b100_w100_d090": "decay 0.90 only",
    "repair5f_static_c100_b100_w100_d095": "mild decay 0.95 only",
    "repair5f_static_c100_b100_w075_d095": "wait reduction + mild decay",
}

MANDATORY_METHOD_ORDER = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "repair5f_bounded_updateparam_selector_force_additive_parity",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5f_bounded_updateparam_selector_runtime",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f_static_c100_b100_w075_d100",
    "repair5f_static_c100_b100_w100_d090",
    "repair5f_static_c100_b100_w100_d095",
    "repair5f_static_c100_b100_w075_d095",
    DETERMINISTIC_RANDOM_METHOD,
]

OPTIONAL_METHOD_ORDER = [
    "repair5e5_crossfold_utility_reranker",
    "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
]

DEFAULT_METHOD_ORDER = [*MANDATORY_METHOD_ORDER, *OPTIONAL_METHOD_ORDER]

PARITY_FIELDS = ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]
SELECTOR_STATIC_OUTCOME_FIELDS = [
    *PARITY_FIELDS,
]
SELECTOR_STATIC_EFFORT_FIELDS = [
    "returned_solutions_count",
    "ltm_iterations",
    "expanded_nodes",
    "high_level_expansions",
    "low_level_pibt_calls",
]


@dataclass(frozen=True)
class MethodSpec:
    method: str
    alias: str
    extra_args: tuple[str, ...] = ()
    requires_runtime_log: bool = False
    optional: bool = False


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


def number(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.mean(clean) if clean else None


def median(values: list[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.median(clean) if clean else None


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


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)))


def run_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (*case_key(row), str(row.get("method")))


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


def completed_keys(rows: list[dict[str, Any]]) -> set[tuple[str, int, int, str]]:
    return {run_key(row) for row in rows}


def candidate_by_id(candidates: list[Candidate]) -> dict[str, Candidate]:
    return {candidate.candidate_id: candidate for candidate in candidates}


def candidate_runtime_path(runtime_root: Path, candidates: dict[str, Candidate], candidate_id: str) -> Path:
    if candidate_id not in candidates:
        raise KeyError(f"candidate lattice is missing {candidate_id}")
    return write_candidate_runtime(runtime_root, candidates[candidate_id])


def runtime_available(path: Path) -> bool:
    required = [
        "features.txt",
        "rules.csv",
        "layer0_weight.csv",
        "rule_head_weight.csv",
        "rule_head_bias.csv",
    ]
    return path.exists() and all((path / name).exists() for name in required)


def stable_random_candidate_id(candidate_ids: list[str], map_name: str, agents: int, seed: int) -> str:
    ordered = sorted(candidate_ids)
    if not ordered:
        raise ValueError("candidate lattice is empty")
    lattice_token = ",".join(ordered)
    digest = hashlib.sha256(
        f"repair5f4_deterministic_random_candidate|{map_name}|{agents}|{seed}|{lattice_token}".encode("utf-8")
    ).digest()
    index = int.from_bytes(digest[:8], "big") % len(ordered)
    return ordered[index]


def scenario_path(scenario_dir: Path, map_name: str, instance_id: int) -> Path:
    return scenario_dir / f"{map_name}-random-{int(instance_id)}.scen"


def largest_contiguous_available_after_25(
    scenario_dir: Path, maps: list[str], requested_ids: list[int]
) -> list[int]:
    ids = sorted({item for item in requested_ids if item > 25})
    out: list[int] = []
    for instance_id in ids:
        if all(scenario_path(scenario_dir, map_name, instance_id).exists() for map_name in maps):
            out.append(instance_id)
            continue
        break
    return out


def audit_and_prepare_scenarios(
    *,
    root: Path,
    source_scenario_dir: Path,
    scenario_dir: Path,
    scenario_metadata: Path,
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    generate_missing: bool,
    base_seed: int,
) -> tuple[list[int], dict[str, Any]]:
    source_missing = [
        {"map": map_name, "instance_id": instance_id}
        for map_name in maps
        for instance_id in instance_ids
        if not scenario_path(source_scenario_dir, map_name, instance_id).exists()
    ]
    initial_missing = [
        {"map": map_name, "instance_id": instance_id}
        for map_name in maps
        for instance_id in instance_ids
        if not scenario_path(scenario_dir, map_name, instance_id).exists()
    ]
    generated: list[dict[str, Any]] = []
    if initial_missing and generate_missing:
        scenario_dir.mkdir(parents=True, exist_ok=True)
        max_agents = max(int(value) for value in agent_counts)
        for map_name in maps:
            map_path = root / MAPS[map_name]
            width, height, grid = read_map(map_path)
            cells = largest_component(width, height, grid)
            if len(cells) < max_agents:
                raise ValueError(f"{map_name}: largest component has {len(cells)} cells, need {max_agents}")
            for instance_id in instance_ids:
                path = scenario_path(scenario_dir, map_name, instance_id)
                if path.exists():
                    continue
                rng = random.Random(map_seed(base_seed, map_name, int(instance_id)))
                starts = rng.sample(cells, max_agents)
                goals = deranged_goals(rng, cells, starts, max_agents)
                text = scenario_text(map_name, width, height, starts, goals)
                path.write_text(text, encoding="utf-8", newline="\n")
                generated.append(
                    {
                        "map": map_name,
                        "instance_id": int(instance_id),
                        "pairs": max_agents,
                        "path": rel(path, root),
                        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    }
                )

    final_missing = [
        {"map": map_name, "instance_id": instance_id}
        for map_name in maps
        for instance_id in instance_ids
        if not scenario_path(scenario_dir, map_name, instance_id).exists()
    ]
    prepared_from_f4_dir = [
        {
            "map": item["map"],
            "instance_id": int(item["instance_id"]),
            "path": rel(scenario_path(scenario_dir, item["map"], int(item["instance_id"])), root),
        }
        for item in source_missing
        if scenario_path(scenario_dir, item["map"], int(item["instance_id"])).exists()
    ]
    effective_instance_ids = list(instance_ids)
    reduced_scope_reason = ""
    if final_missing and not generate_missing:
        effective_instance_ids = largest_contiguous_available_after_25(scenario_dir, maps, instance_ids)
        reduced_scope_reason = "missing scenarios and --no-generate-missing-scenarios was used"
        if not effective_instance_ids:
            raise FileNotFoundError("no contiguous fresh scenario range after 25 is available")
    elif final_missing:
        raise FileNotFoundError(f"missing generated scenarios: {final_missing[:10]}")

    metadata = {
        "schema_version": "phase5p5_repair5f4_scenario_generation_v1",
        "created_at": datetime.now().isoformat(),
        "source_scenario_dir": rel(source_scenario_dir, root),
        "scenario_dir": rel(scenario_dir, root),
        "scenario_metadata": rel(scenario_metadata, root),
        "requested_maps": list(maps),
        "requested_instance_ids": [int(value) for value in instance_ids],
        "effective_instance_ids": [int(value) for value in effective_instance_ids],
        "agent_counts": [int(value) for value in agent_counts],
        "source_missing_count": len(source_missing),
        "source_missing_examples": source_missing[:20],
        "initial_missing_count": len(initial_missing),
        "initial_missing_examples": initial_missing[:20],
        "generated_missing_scenarios": bool(generated) or bool(prepared_from_f4_dir),
        "generated_count": len(generated) if generated else len(prepared_from_f4_dir),
        "generated_examples": generated[:20] if generated else prepared_from_f4_dir[:20],
        "final_missing_count": len(final_missing),
        "final_missing_examples": final_missing[:20],
        "reduced_scope_reason": reduced_scope_reason,
        "generator_policy": {
            "source": "scripts/generate_phase1a_scenarios.py functions",
            "script_version": SCENARIO_GENERATOR_VERSION,
            "base_seed": int(base_seed),
            "seed_function": "sha256(script_version|base_seed|map_name|instance_id)",
            "equivalent_command": (
                "python scripts/generate_phase1a_scenarios.py "
                "--manifest <f4 maps with instances 26..45> "
                f"--output-dir {rel(scenario_dir, root)} --base-seed {int(base_seed)}"
            ),
        },
    }
    scenario_metadata.parent.mkdir(parents=True, exist_ok=True)
    scenario_metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return effective_instance_ids, metadata


def build_method_spec(
    *,
    method: str,
    selector_runtime: Path,
    e5_runtime: Path,
    e5_shuffled_runtime: Path,
    runtime_root: Path,
    candidates: dict[str, Candidate],
    candidate_ids: list[str],
    key: tuple[str, int, int],
) -> MethodSpec | None:
    if method in {
        "lacam_star_ltm",
        "always_additive_defer",
        "repair5f_candidate_additive_ltm",
        "repair5f_bounded_updateparam_selector_force_additive_parity",
        "laur_disable",
        "laur_force_additive_direct",
    }:
        return MethodSpec(method, method)
    if method == "repair5f_bounded_updateparam_selector_runtime":
        return MethodSpec(
            method,
            method,
            ("--laur-model-path", str(selector_runtime), "--laur-safety-threshold", "1.01"),
            True,
        )
    if method.startswith(STATIC_PREFIX):
        candidate_id = method[len(STATIC_PREFIX) :]
        runtime = candidate_runtime_path(runtime_root, candidates, candidate_id)
        return MethodSpec(
            "lacam_star_lau_ltm",
            method,
            ("--laur-model-path", str(runtime), "--laur-safety-threshold", "1.01"),
            True,
        )
    if method == DETERMINISTIC_RANDOM_METHOD:
        candidate_id = stable_random_candidate_id(candidate_ids, key[0], key[1], key[2])
        runtime = candidate_runtime_path(runtime_root, candidates, candidate_id)
        return MethodSpec(
            "lacam_star_lau_ltm",
            method,
            ("--laur-model-path", str(runtime), "--laur-safety-threshold", "1.01"),
            True,
        )
    if method == "repair5e5_crossfold_utility_reranker":
        if not runtime_available(e5_runtime):
            return None
        return MethodSpec(
            "lacam_star_lau_ltm",
            method,
            ("--laur-model-path", str(e5_runtime), "--laur-safety-threshold", "0.30", "--laur-ood-z-threshold", "4.25"),
            True,
            True,
        )
    if method == "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic":
        if not runtime_available(e5_shuffled_runtime):
            return None
        return MethodSpec(
            "lacam_star_lau_ltm",
            method,
            (
                "--laur-model-path",
                str(e5_shuffled_runtime),
                "--laur-safety-threshold",
                "0.30",
                "--laur-ood-z-threshold",
                "4.25",
            ),
            True,
            True,
        )
    raise KeyError(f"unsupported F4 method: {method}")


def active_methods(methods: list[str], e5_runtime: Path, e5_shuffled_runtime: Path) -> tuple[list[str], list[dict[str, str]]]:
    active: list[str] = []
    skipped: list[dict[str, str]] = []
    for method in methods:
        if method == "repair5e5_crossfold_utility_reranker" and not runtime_available(e5_runtime):
            skipped.append({"method": method, "reason": "runtime_unavailable"})
            continue
        if method == "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic" and not runtime_available(
            e5_shuffled_runtime
        ):
            skipped.append({"method": method, "reason": "runtime_unavailable"})
            continue
        active.append(method)
    return active, skipped


def run_grid(
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
    methods: list[str],
    selector_runtime: Path,
    e5_runtime: Path,
    e5_shuffled_runtime: Path,
    runtime_root: Path,
    candidates: dict[str, Candidate],
    candidate_ids: list[str],
    completed: set[tuple[str, int, int, str]],
    chunk_size: int,
) -> int:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    runs_started = 0
    for map_name in maps:
        map_path = root / MAPS[map_name]
        if not map_path.exists():
            raise FileNotFoundError(map_path)
        for seed in instance_ids:
            scen_path = scenario_path(scenario_dir, map_name, seed)
            if not scen_path.exists():
                raise FileNotFoundError(scen_path)
            for agents in agent_counts:
                key = (map_name, int(agents), int(seed))
                for method in methods:
                    run_id = (*key, method)
                    if run_id in completed:
                        continue
                    if chunk_size > 0 and runs_started >= chunk_size:
                        return runs_started
                    spec = build_method_spec(
                        method=method,
                        selector_runtime=selector_runtime,
                        e5_runtime=e5_runtime,
                        e5_shuffled_runtime=e5_shuffled_runtime,
                        runtime_root=runtime_root,
                        candidates=candidates,
                        candidate_ids=candidate_ids,
                        key=key,
                    )
                    if spec is None:
                        continue
                    extra = list(spec.extra_args)
                    if spec.requires_runtime_log:
                        extra.extend(["--laur-update-log-jsonl", str(update_log)])
                    if spec.alias != spec.method:
                        extra.extend(["--method-alias", spec.alias])
                    command = [
                        str(binary),
                        "--method",
                        spec.method,
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
                        "phase5p5-repair5f4-static-updateparams-validation",
                        "--project-commit",
                        git_value(["rev-parse", "--short", "HEAD"], root),
                        "--external-commit",
                        "local",
                        "--branch",
                        git_value(["branch", "--show-current"], root),
                        "--dirty",
                        dirty_state(root),
                        "--platform",
                        "Windows Repair5F.4 static UpdateParams validation",
                        *extra,
                    ]
                    completed_process = subprocess.run(command, cwd=root, text=True, capture_output=True)
                    command_row = {
                        "method": spec.alias,
                        "map": map_name,
                        "agents": int(agents),
                        "seed": int(seed),
                        "returncode": completed_process.returncode,
                        "command": command,
                        "stdout": completed_process.stdout.strip()[-500:],
                        "stderr": completed_process.stderr.strip()[-500:],
                    }
                    with command_log.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(command_row, sort_keys=True) + "\n")
                    runs_started += 1
                    if completed_process.returncode != 0:
                        raise RuntimeError(
                            f"solver failed for {spec.alias} {map_name} a{agents} s{seed}: "
                            f"{completed_process.stderr}"
                        )
    return runs_started


def selected_candidate_from_row(row: dict[str, Any]) -> str:
    selected = row.get("laur_selected_rules")
    if isinstance(selected, dict) and selected:
        ranked = sorted(selected.items(), key=lambda item: (-int(item[1]), str(item[0])))
        return str(ranked[0][0])
    method = str(row.get("method", ""))
    if method in {
        "lacam_star_ltm",
        "always_additive_defer",
        "repair5f_candidate_additive_ltm",
        "repair5f_bounded_updateparam_selector_force_additive_parity",
        "laur_disable",
        "laur_force_additive_direct",
    }:
        return "additive_ltm"
    if method.startswith(STATIC_PREFIX):
        return method[len(STATIC_PREFIX) :]
    if boolish(row.get("laur_force_additive")):
        return "additive_ltm"
    return ""


def build_paired(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[case_key(row)][str(row.get("method"))] = row
    paired: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        base = methods.get(BASE_METHOD)
        if base is None:
            continue
        base_ratio = number(base.get("sum_of_loss_ratio"))
        for method, row in sorted(methods.items()):
            if method == BASE_METHOD:
                continue
            ratio = number(row.get("sum_of_loss_ratio"))
            delta = ratio - base_ratio if math.isfinite(ratio) and math.isfinite(base_ratio) else math.nan
            paired.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": row.get("scen", ""),
                    "method": method,
                    "success": boolish(row.get("success")),
                    "ltm_success": boolish(base.get("success")),
                    "sum_of_loss": row.get("sum_of_loss", ""),
                    "ltm_sum_of_loss": base.get("sum_of_loss", ""),
                    "sum_of_loss_ratio": ratio if math.isfinite(ratio) else "",
                    "ltm_sum_of_loss_ratio": base_ratio if math.isfinite(base_ratio) else "",
                    "delta_ratio_vs_ltm": delta if math.isfinite(delta) else "",
                    "better_vs_ltm": math.isfinite(delta) and delta < -1.0e-12,
                    "equal_vs_ltm": math.isfinite(delta) and abs(delta) <= 1.0e-12,
                    "worse_vs_ltm": math.isfinite(delta) and delta > 1.0e-12,
                    "selected_candidate_id": selected_candidate_from_row(row),
                    "laur_update_mode": row.get("laur_update_mode", ""),
                    "laur_model_path": row.get("laur_model_path", ""),
                    "expanded_delta_vs_ltm": number(row.get("expanded_nodes"), 0.0) - number(base.get("expanded_nodes"), 0.0),
                    "low_level_pibt_delta_vs_ltm": number(row.get("low_level_pibt_calls"), 0.0)
                    - number(base.get("low_level_pibt_calls"), 0.0),
                    "ttfs_delta_vs_ltm": number(row.get("time_to_first_solution_ms"), 0.0)
                    - number(base.get("time_to_first_solution_ms"), 0.0),
                }
            )
    return paired


def bootstrap_mean_ci(values: list[float], method: str, samples: int = 2000) -> tuple[float | None, float | None, float | None]:
    clean = [value for value in values if math.isfinite(value)]
    if not clean:
        return None, None, None
    digest = hashlib.sha256(method.encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    means: list[float] = []
    for _ in range(samples):
        draw = [clean[rng.randrange(len(clean))] for _ in clean]
        means.append(statistics.mean(draw))
    means.sort()
    lower = means[int(0.025 * (len(means) - 1))]
    upper = means[int(0.975 * (len(means) - 1))]
    prob_lt_zero = sum(1 for value in means if value < 0.0) / len(means)
    return lower, upper, prob_lt_zero


def summarize_method(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    deltas = [number(row.get("delta_ratio_vs_ltm")) for row in rows]
    clean_deltas = [value for value in deltas if math.isfinite(value)]
    ci_lower, ci_upper, prob_lt_zero = bootstrap_mean_ci(clean_deltas, method)
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["map"]), int(row["agents"]))].append(row)
    candidate_counts = Counter(str(row.get("selected_candidate_id", "")) for row in rows)
    nonadditive = [row for row in rows if row.get("selected_candidate_id") not in {"", "additive_ltm"}]
    return {
        "rows": len(rows),
        "better": sum(1 for value in deltas if math.isfinite(value) and value < -1.0e-12),
        "equal": sum(1 for value in deltas if math.isfinite(value) and abs(value) <= 1.0e-12),
        "worse": sum(1 for value in deltas if math.isfinite(value) and value > 1.0e-12),
        "mean_delta_ratio_vs_ltm": mean(clean_deltas),
        "median_delta_ratio_vs_ltm": median(clean_deltas),
        "bootstrap_95ci_mean_delta_ratio_vs_ltm": [ci_lower, ci_upper],
        "bootstrap_probability_mean_delta_lt_0": prob_lt_zero,
        "ratio_worse_than_ltm_groups": sum(
            1
            for group in grouped.values()
            if (mean([number(row.get("delta_ratio_vs_ltm")) for row in group]) or 0.0) > 1.0e-12
        ),
        "success_worse_than_ltm_groups": sum(
            1
            for group in grouped.values()
            if sum(1 for row in group if boolish(row.get("success")))
            < sum(1 for row in group if boolish(row.get("ltm_success")))
        ),
        "selected_nonadditive_cases": len(nonadditive),
        "selected_candidate_distribution": dict(sorted(candidate_counts.items())),
    }


def summarize_paired(paired: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in paired:
        grouped[str(row["method"])].append(row)
    return {method: summarize_method(rows, method) for method, rows in sorted(grouped.items())}


def by_map_agent_rows(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in paired:
        grouped[(str(row["method"]), str(row["map"]), int(row["agents"]))].append(row)
    out: list[dict[str, Any]] = []
    for (method, map_name, agents), rows in sorted(grouped.items()):
        deltas = [number(row.get("delta_ratio_vs_ltm")) for row in rows]
        out.append(
            {
                "method": method,
                "map": map_name,
                "agents": agents,
                "rows": len(rows),
                "better": sum(1 for value in deltas if math.isfinite(value) and value < -1.0e-12),
                "equal": sum(1 for value in deltas if math.isfinite(value) and abs(value) <= 1.0e-12),
                "worse": sum(1 for value in deltas if math.isfinite(value) and value > 1.0e-12),
                "mean_delta_ratio_vs_ltm": mean([value for value in deltas if math.isfinite(value)]),
            }
        )
    return out


def parity_exact(rows: list[dict[str, Any]], method: str) -> bool:
    by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[case_key(row)][str(row.get("method"))] = row
    observed = 0
    for methods in by_case.values():
        base = methods.get(BASE_METHOD)
        other = methods.get(method)
        if base is None or other is None:
            return False
        observed += 1
        for field in PARITY_FIELDS:
            if base.get(field) != other.get(field):
                return False
    return observed > 0


def selector_static_metric_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_case_method = {(*case_key(row), str(row.get("method"))): row for row in rows}
    outcome_mismatches: list[dict[str, Any]] = []
    effort_mismatches: list[dict[str, Any]] = []
    selector_rows = 0
    for key_method, selector in sorted(by_case_method.items()):
        map_name, agents, seed, method = key_method
        if method != "repair5f_bounded_updateparam_selector_runtime":
            continue
        selector_rows += 1
        static = by_case_method.get((map_name, agents, seed, f"{STATIC_PREFIX}{LOCKED_MAIN_CANDIDATE}"))
        if static is None:
            outcome_mismatches.append({"map": map_name, "agents": agents, "seed": seed, "field": "row_presence"})
            continue
        for field in SELECTOR_STATIC_OUTCOME_FIELDS:
            if selector.get(field) != static.get(field):
                outcome_mismatches.append(
                    {
                        "map": map_name,
                        "agents": agents,
                        "seed": seed,
                        "field": field,
                        "selector_value": selector.get(field),
                        "static_value": static.get(field),
                    }
                )
        for field in SELECTOR_STATIC_EFFORT_FIELDS:
            if selector.get(field) != static.get(field):
                effort_mismatches.append(
                    {
                        "map": map_name,
                        "agents": agents,
                        "seed": seed,
                        "field": field,
                        "selector_value": selector.get(field),
                        "static_value": static.get(field),
                    }
                )
    return {
        "selector_static_runtime_metrics_equal": not outcome_mismatches and selector_rows > 0,
        "selector_static_runtime_effort_equal": not effort_mismatches and selector_rows > 0,
        "selector_rows": selector_rows,
        "outcome_mismatch_count": len(outcome_mismatches),
        "outcome_mismatch_examples": outcome_mismatches[:20],
        "effort_mismatch_count": len(effort_mismatches),
        "effort_mismatch_examples": effort_mismatches[:20],
        "mismatch_count": len(outcome_mismatches) + len(effort_mismatches),
        "mismatch_examples": [*outcome_mismatches[:10], *effort_mismatches[:10]],
    }


def component_ablation_rows(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case_method = {(*case_key(row), str(row["method"])): row for row in paired}
    out: list[dict[str, Any]] = []
    full_method = f"{STATIC_PREFIX}{LOCKED_MAIN_CANDIDATE}"
    for method, label in COMPONENT_ABLATIONS.items():
        full_deltas: list[float] = []
        ablation_deltas: list[float] = []
        better = equal = worse = 0
        for key_method, full in sorted(by_case_method.items()):
            map_name, agents, seed, current_method = key_method
            if current_method != full_method:
                continue
            ablation = by_case_method.get((map_name, agents, seed, method))
            if ablation is None:
                continue
            full_delta = number(full.get("delta_ratio_vs_ltm"))
            ablation_delta = number(ablation.get("delta_ratio_vs_ltm"))
            if not math.isfinite(full_delta) or not math.isfinite(ablation_delta):
                continue
            full_deltas.append(full_delta)
            ablation_deltas.append(ablation_delta)
            diff = full_delta - ablation_delta
            if diff < -1.0e-12:
                better += 1
            elif abs(diff) <= 1.0e-12:
                equal += 1
            else:
                worse += 1
        full_mean = mean(full_deltas)
        ablation_mean = mean(ablation_deltas)
        out.append(
            {
                "component_ablation": method,
                "mechanism": label,
                "rows": len(full_deltas),
                "full_mean_delta_ratio_vs_ltm": full_mean,
                "ablation_mean_delta_ratio_vs_ltm": ablation_mean,
                "full_minus_ablation_mean_delta": (
                    full_mean - ablation_mean
                    if full_mean is not None and ablation_mean is not None
                    else None
                ),
                "full_better_cases": better,
                "full_equal_cases": equal,
                "full_worse_cases": worse,
                "full_mean_beats_or_ties_ablation": (
                    full_mean is not None and ablation_mean is not None and full_mean <= ablation_mean + 1.0e-12
                ),
            }
        )
    return out


def worst_group_and_cases(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["map"]), int(row["agents"]))].append(row)
    group_rows: list[dict[str, Any]] = []
    for (map_name, agents), items in grouped.items():
        deltas = [number(item.get("delta_ratio_vs_ltm")) for item in items]
        group_rows.append(
            {
                "map": map_name,
                "agents": agents,
                "rows": len(items),
                "mean_delta_ratio_vs_ltm": mean([value for value in deltas if math.isfinite(value)]),
                "better": sum(1 for value in deltas if math.isfinite(value) and value < -1.0e-12),
                "equal": sum(1 for value in deltas if math.isfinite(value) and abs(value) <= 1.0e-12),
                "worse": sum(1 for value in deltas if math.isfinite(value) and value > 1.0e-12),
            }
        )
    worst_group = max(group_rows, key=lambda row: number(row.get("mean_delta_ratio_vs_ltm"), -math.inf)) if group_rows else {}
    worst_cases = sorted(
        rows,
        key=lambda row: number(row.get("delta_ratio_vs_ltm"), -math.inf),
        reverse=True,
    )[:5]
    return worst_group, worst_cases


def build_gates(
    *,
    stats: dict[str, dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    expected_rows: int,
    missing_rows: int,
    schema_errors: list[str],
    instance_ids: list[int],
    selector_static_audit: dict[str, Any],
) -> dict[str, Any]:
    main_method = f"{STATIC_PREFIX}{LOCKED_MAIN_CANDIDATE}"
    main = stats.get(main_method, {})
    random_diag = stats.get(DETERMINISTIC_RANDOM_METHOD, {})
    ci = main.get("bootstrap_95ci_mean_delta_ratio_vs_ltm") or [None, None]
    main_mean = main.get("mean_delta_ratio_vs_ltm")
    random_mean = random_diag.get("mean_delta_ratio_vs_ltm")
    selector_dist = stats.get("repair5f_bounded_updateparam_selector_runtime", {}).get(
        "selected_candidate_distribution", {}
    )
    support_overlap = sorted(set(instance_ids) & SUPPORT_IDS)
    f2f3_overlap = sorted(set(instance_ids) & F2F3_HOLDOUT_IDS)
    return {
        "full_expected_rows": len(raw_rows) == expected_rows and missing_rows == 0,
        "schema_errors_eq_0": len(schema_errors) == 0,
        "missing_rows_eq_0": missing_rows == 0,
        "support_validation_overlap_count_eq_0": len(support_overlap) == 0,
        "f2f3_holdout_validation_overlap_count_eq_0": len(f2f3_overlap) == 0,
        "force_additive_parity_exact": parity_exact(raw_rows, "repair5f_bounded_updateparam_selector_force_additive_parity"),
        "exact_additive_candidate_parity_exact": parity_exact(raw_rows, "repair5f_candidate_additive_ltm"),
        "laur_disable_parity_exact": parity_exact(raw_rows, "laur_disable"),
        "laur_force_additive_direct_parity_exact": parity_exact(raw_rows, "laur_force_additive_direct"),
        "selector_static_runtime_metrics_equal": bool(selector_static_audit.get("selector_static_runtime_metrics_equal")),
        "selector_selected_c100_b100_w075_d090_all_cases": selector_dist == {LOCKED_MAIN_CANDIDATE: main.get("rows")},
        "main_static_better_gt_worse": int(main.get("better") or 0) > int(main.get("worse") or 0),
        "main_static_mean_delta_ratio_vs_ltm_lt_0": main_mean is not None and float(main_mean) < 0.0,
        "main_static_bootstrap_ci_upper_le_0": ci[1] is not None and float(ci[1]) <= 0.0,
        "main_static_ratio_worse_than_ltm_groups_le_1": int(main.get("ratio_worse_than_ltm_groups") or 0) <= 1,
        "main_static_success_worse_than_ltm_groups_eq_0": int(main.get("success_worse_than_ltm_groups") or 0) == 0,
        "main_static_beats_deterministic_random_candidate_diagnostic": (
            main_mean is not None and random_mean is not None and float(main_mean) < float(random_mean)
        ),
        "phase5p5_allowed_false": True,
        "phase6_allowed_false": True,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary["paired_method_stats"]
    gates = summary["mandatory_gates"]
    main_method = f"{STATIC_PREFIX}{LOCKED_MAIN_CANDIDATE}"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.4 Static UpdateParams Larger Validation\n\n")
        handle.write("Diagnostic-only. Phase5.5 and Phase6 remain forbidden.\n\n")
        handle.write("## Scope\n\n")
        scope = summary["scope"]
        handle.write(f"- maps: `{scope['maps']}`\n")
        handle.write(f"- agent_counts: `{scope['agent_counts']}`\n")
        handle.write(f"- instance_ids: `{scope['instance_ids']}`\n")
        handle.write(f"- time_limit_sec: `{scope['time_limit_sec']}`\n")
        handle.write(f"- ltm_max_iterations: `{scope['ltm_max_iterations']}`\n")
        handle.write(f"- scenario_dir: `{summary['scenario_audit']['scenario_dir']}`\n\n")
        handle.write("## Method Summary\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta | 95% CI | selected candidates |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---|---|\n")
        for method in scope["methods"]:
            if method == BASE_METHOD:
                continue
            row = stats.get(method)
            if not row:
                continue
            ci = row.get("bootstrap_95ci_mean_delta_ratio_vs_ltm")
            handle.write(
                f"| `{method}` | {row.get('rows')} | {row.get('better')} | {row.get('equal')} | "
                f"{row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} | `{ci}` | "
                f"`{row.get('selected_candidate_distribution')}` |\n"
            )
        handle.write("\n## Main Static Rule\n\n")
        main = stats.get(main_method, {})
        handle.write(f"- locked candidate: `{LOCKED_MAIN_CANDIDATE}`\n")
        handle.write(f"- better / equal / worse: `{main.get('better')} / {main.get('equal')} / {main.get('worse')}`\n")
        handle.write(f"- mean_delta_ratio_vs_ltm: `{main.get('mean_delta_ratio_vs_ltm')}`\n")
        handle.write(f"- median_delta_ratio_vs_ltm: `{main.get('median_delta_ratio_vs_ltm')}`\n")
        handle.write(f"- bootstrap_95ci_mean_delta_ratio_vs_ltm: `{main.get('bootstrap_95ci_mean_delta_ratio_vs_ltm')}`\n")
        handle.write(f"- bootstrap_probability_mean_delta_lt_0: `{main.get('bootstrap_probability_mean_delta_lt_0')}`\n")
        handle.write(f"- worst_group: `{summary['main_static_worst_group']}`\n")
        handle.write("\n## Component Ablation\n\n")
        handle.write("| ablation | mechanism | rows | full mean | ablation mean | full mean beats/ties |\n")
        handle.write("|---|---|---:|---:|---:|---|\n")
        for row in summary["component_ablation_rows"]:
            handle.write(
                f"| `{row['component_ablation']}` | {row['mechanism']} | {row['rows']} | "
                f"{row['full_mean_delta_ratio_vs_ltm']} | {row['ablation_mean_delta_ratio_vs_ltm']} | "
                f"{row['full_mean_beats_or_ties_ablation']} |\n"
            )
        handle.write("\n## Gates\n\n")
        for key, value in gates.items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Interpretation\n\n")
        handle.write(summary["interpretation"] + "\n")


def write_audit_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.4 Validation Audit\n\n")
        handle.write("Diagnostic-only audit for row coverage, schema, parity, and static equality.\n\n")
        handle.write(f"- expected_rows: `{summary['expected_rows']}`\n")
        handle.write(f"- raw_rows_before_dedupe: `{summary['raw_rows_before_dedupe']}`\n")
        handle.write(f"- raw_rows_after_dedupe: `{summary['raw_rows_after_dedupe']}`\n")
        handle.write(f"- missing_rows: `{summary['missing_rows']}`\n")
        handle.write(f"- schema_errors: `{len(summary['schema_errors'])}`\n")
        handle.write(f"- selector_static_mismatch_count: `{summary['selector_static_audit']['mismatch_count']}`\n\n")
        handle.write("## Mandatory Gates\n\n")
        for key, value in summary["mandatory_gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")


def write_freshness_audit(path: Path, audit_json: Path, summary: dict[str, Any]) -> None:
    freshness = summary["freshness_audit"]
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(json.dumps(freshness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.4 Freshness and Leakage Audit\n\n")
        handle.write("Diagnostic-only. F4 outcomes did not choose or retune the locked candidate.\n\n")
        for key, value in freshness.items():
            handle.write(f"- `{key}`: `{value}`\n")


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    passed = bool(summary["mandatory_gates_passed"])
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.4 Validation Decision\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- mandatory_gates_passed: `{passed}`\n\n")
        if passed:
            handle.write(
                "F4-A passes the required diagnostic gates. Recommend Repair5F.4B time-budget and scope stress "
                "validation with the same locked static rule and fresh IDs not used in F4-A if possible.\n"
            )
        else:
            failed = [key for key, value in summary["mandatory_gates"].items() if not value]
            handle.write(
                "F4-A does not pass all required diagnostic gates. Do not promote and do not claim Phase5.5 or "
                "Phase6 evidence.\n\n"
            )
            handle.write(f"Failed gates: `{failed}`\n\n")
            handle.write("Analyze the worst groups and component ablations before changing selector design.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--scenario-base-seed", type=int, default=20260522)
    parser.add_argument("--generate-missing-scenarios", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--candidate-lattice-csv", type=Path, default=Path(DEFAULT_CANDIDATE_CSV))
    parser.add_argument("--selector-runtime-dir", type=Path, default=Path(DEFAULT_SELECTOR_RUNTIME))
    parser.add_argument("--repair5e5-runtime-dir", type=Path, default=Path(DEFAULT_E5_RUNTIME))
    parser.add_argument("--repair5e5-shuffled-runtime-dir", type=Path, default=Path(DEFAULT_E5_SHUFFLED_RUNTIME))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--component-ablation-csv", type=Path, default=Path(DEFAULT_COMPONENT_ABLATION))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_AUDIT_REPORT))
    parser.add_argument("--freshness-audit-report", type=Path, default=Path(DEFAULT_FRESHNESS_AUDIT))
    parser.add_argument("--freshness-audit-summary-json", type=Path, default=Path(DEFAULT_FRESHNESS_AUDIT_JSON))
    parser.add_argument("--decision-report", type=Path, default=Path(DEFAULT_DECISION))
    parser.add_argument("--maps", nargs="+", choices=sorted(MAPS), default=list(MAPS))
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(26, 46)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHOD_ORDER)
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve(args.binary, root)
    source_scenario_dir = resolve(args.source_scenario_dir, root)
    scenario_dir = resolve(args.scenario_dir, root)
    scenario_metadata = resolve(args.scenario_metadata_json, root)
    candidate_csv = resolve(args.candidate_lattice_csv, root)
    selector_runtime = resolve(args.selector_runtime_dir, root)
    e5_runtime = resolve(args.repair5e5_runtime_dir, root)
    e5_shuffled_runtime = resolve(args.repair5e5_shuffled_runtime_dir, root)
    runtime_root = resolve(args.runtime_root, root)
    output_dir = resolve(args.output_dir, root)
    output_jsonl = resolve(args.output_jsonl, root)
    paired_csv = resolve(args.paired_csv, root)
    summary_csv = resolve(args.summary_csv, root)
    by_map_agent_csv = resolve(args.by_map_agent_csv, root)
    component_ablation_csv = resolve(args.component_ablation_csv, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    audit_report = resolve(args.audit_report, root)
    freshness_audit_report = resolve(args.freshness_audit_report, root)
    freshness_audit_json = resolve(args.freshness_audit_summary_json, root)
    decision_report = resolve(args.decision_report, root)
    command_log = output_jsonl.with_name(output_jsonl.stem + "_commands.jsonl")
    update_log = output_jsonl.with_name(output_jsonl.stem + "_laur_updates.jsonl")

    if args.overwrite and args.resume:
        raise ValueError("--overwrite and --resume cannot both be set")
    if int(args.chunk_size) < 0:
        raise ValueError("--chunk-size must be >= 0")
    for path in [candidate_csv, selector_runtime]:
        if not path.exists():
            raise FileNotFoundError(path)

    candidates = candidate_by_id(read_candidates(candidate_csv))
    candidate_ids = sorted(candidates)
    if LOCKED_MAIN_CANDIDATE not in candidates:
        raise KeyError(f"locked candidate missing from lattice: {LOCKED_MAIN_CANDIDATE}")

    methods, skipped_methods = active_methods(list(args.methods), e5_runtime, e5_shuffled_runtime)
    maps = list(args.maps)
    agent_counts = [int(value) for value in args.agent_counts]
    requested_instance_ids = [int(value) for value in args.instance_ids]
    instance_ids, scenario_audit = audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=source_scenario_dir,
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        maps=maps,
        agent_counts=agent_counts,
        instance_ids=requested_instance_ids,
        generate_missing=bool(args.generate_missing_scenarios),
        base_seed=int(args.scenario_base_seed),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()
    if not args.skip_solver and not binary.exists():
        raise FileNotFoundError(binary)

    completed: set[tuple[str, int, int, str]] = set()
    if output_jsonl.exists() and args.resume:
        completed = completed_keys(dedupe_rows(read_jsonl(output_jsonl)))
    elif output_jsonl.exists() and not args.skip_solver:
        raise FileExistsError(f"output JSONL already exists: {output_jsonl}")

    runs_started = 0
    if not args.skip_solver:
        runs_started = run_grid(
            root=root,
            binary=binary,
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            update_log=update_log,
            maps=maps,
            agent_counts=agent_counts,
            instance_ids=instance_ids,
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=methods,
            selector_runtime=selector_runtime,
            e5_runtime=e5_runtime,
            e5_shuffled_runtime=e5_shuffled_runtime,
            runtime_root=runtime_root,
            candidates=candidates,
            candidate_ids=candidate_ids,
            completed=completed,
            chunk_size=int(args.chunk_size),
        )

    raw_jsonl_rows = read_jsonl(output_jsonl)
    raw_rows = dedupe_rows(raw_jsonl_rows)
    observed = completed_keys(raw_rows)
    expected = {
        (map_name, int(agents), int(seed), method)
        for map_name in maps
        for agents in agent_counts
        for seed in instance_ids
        for method in methods
    }
    missing = sorted(expected - observed)
    schema_errors: list[str] = []
    for index, row in enumerate(raw_rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))

    paired = build_paired(raw_rows)
    stats = summarize_paired(paired)
    by_group = by_map_agent_rows(paired)
    component_rows = component_ablation_rows(paired)
    selector_static_audit = selector_static_metric_audit(raw_rows)
    main_method = f"{STATIC_PREFIX}{LOCKED_MAIN_CANDIDATE}"
    main_rows = [row for row in paired if row["method"] == main_method]
    worst_group, worst_cases = worst_group_and_cases(main_rows)
    gates = build_gates(
        stats=stats,
        raw_rows=raw_rows,
        expected_rows=len(expected),
        missing_rows=len(missing),
        schema_errors=schema_errors,
        instance_ids=instance_ids,
        selector_static_audit=selector_static_audit,
    )
    freshness = {
        "schema_version": "phase5p5_repair5f4_freshness_audit_v1",
        "created_at": datetime.now().isoformat(),
        "support_ids_1_20_not_in_f4_validation": len(set(instance_ids) & SUPPORT_IDS) == 0,
        "support_validation_overlap_count": len(set(instance_ids) & SUPPORT_IDS),
        "support_validation_overlap_ids": sorted(set(instance_ids) & SUPPORT_IDS),
        "f2f3_holdout_ids_21_25_not_in_f4_validation": len(set(instance_ids) & F2F3_HOLDOUT_IDS) == 0,
        "f2f3_holdout_validation_overlap_count": len(set(instance_ids) & F2F3_HOLDOUT_IDS),
        "f2f3_holdout_validation_overlap_ids": sorted(set(instance_ids) & F2F3_HOLDOUT_IDS),
        "f4_outcomes_not_used_to_choose_locked_rule": True,
        "locked_rule_source": "Repair5F.2/F3.1 support-trained selector; fixed before F4",
        "runtime_selector_selected_c100_b100_w075_d090_for_every_case": gates[
            "selector_selected_c100_b100_w075_d090_all_cases"
        ],
        "selector_static_metrics_identical": selector_static_audit["selector_static_runtime_metrics_equal"],
        "force_additive_parity_exact": gates["force_additive_parity_exact"],
        "exact_additive_candidate_parity_exact": gates["exact_additive_candidate_parity_exact"],
        "laur_disable_parity_exact": gates["laur_disable_parity_exact"],
        "laur_force_additive_direct_parity_exact": gates["laur_force_additive_direct_parity_exact"],
        "schema_errors": len(schema_errors),
        "missing_rows": len(missing),
        "scenario_audit": scenario_audit,
    }
    mandatory_gates_passed = all(bool(value) for value in gates.values())
    interpretation = (
        "F4-A passes all mandatory gates for the locked support-trained static bounded UpdateParams rule. "
        "This still does not permit Phase5.5 or Phase6; the correct next step is F4-B stress validation."
        if mandatory_gates_passed
        else "F4-A does not pass all mandatory gates. Treat the result as diagnostic only; do not promote or retune "
        "from F4 outcomes."
    )

    paired_fields = [
        "map",
        "agents",
        "seed",
        "scen",
        "method",
        "success",
        "ltm_success",
        "sum_of_loss",
        "ltm_sum_of_loss",
        "sum_of_loss_ratio",
        "ltm_sum_of_loss_ratio",
        "delta_ratio_vs_ltm",
        "better_vs_ltm",
        "equal_vs_ltm",
        "worse_vs_ltm",
        "selected_candidate_id",
        "laur_update_mode",
        "laur_model_path",
        "expanded_delta_vs_ltm",
        "low_level_pibt_delta_vs_ltm",
        "ttfs_delta_vs_ltm",
    ]
    write_csv(paired_csv, paired, paired_fields)
    summary_rows = [{"method": method, **row} for method, row in stats.items()]
    summary_fields = [
        "method",
        "rows",
        "better",
        "equal",
        "worse",
        "mean_delta_ratio_vs_ltm",
        "median_delta_ratio_vs_ltm",
        "bootstrap_95ci_mean_delta_ratio_vs_ltm",
        "bootstrap_probability_mean_delta_lt_0",
        "ratio_worse_than_ltm_groups",
        "success_worse_than_ltm_groups",
        "selected_nonadditive_cases",
        "selected_candidate_distribution",
    ]
    write_csv(summary_csv, summary_rows, summary_fields)
    write_csv(
        by_map_agent_csv,
        by_group,
        ["method", "map", "agents", "rows", "better", "equal", "worse", "mean_delta_ratio_vs_ltm"],
    )
    write_csv(
        component_ablation_csv,
        component_rows,
        [
            "component_ablation",
            "mechanism",
            "rows",
            "full_mean_delta_ratio_vs_ltm",
            "ablation_mean_delta_ratio_vs_ltm",
            "full_minus_ablation_mean_delta",
            "full_better_cases",
            "full_equal_cases",
            "full_worse_cases",
            "full_mean_beats_or_ties_ablation",
        ],
    )

    summary = {
        "schema_version": "phase5p5_repair5f4_static_updateparams_validation_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "locked_main_candidate": LOCKED_MAIN_CANDIDATE,
        "f4_outcomes_used_for_retuning": False,
        "scope": {
            "maps": maps,
            "agent_counts": agent_counts,
            "instance_ids": instance_ids,
            "requested_instance_ids": requested_instance_ids,
            "time_limit_sec": float(args.time_limit_sec),
            "ltm_max_iterations": int(args.ltm_max_iterations),
            "methods": methods,
            "skipped_methods": skipped_methods,
        },
        "scenario_audit": scenario_audit,
        "raw_jsonl": rel(output_jsonl, root),
        "command_log_jsonl": rel(command_log, root),
        "laur_update_log_jsonl": rel(update_log, root),
        "paired_csv": rel(paired_csv, root),
        "summary_csv": rel(summary_csv, root),
        "by_map_agent_csv": rel(by_map_agent_csv, root),
        "component_ablation_csv": rel(component_ablation_csv, root),
        "report": rel(report, root),
        "summary_json": rel(summary_json, root),
        "audit_report": rel(audit_report, root),
        "freshness_audit_report": rel(freshness_audit_report, root),
        "freshness_audit_summary_json": rel(freshness_audit_json, root),
        "decision_report": rel(decision_report, root),
        "runs_started_this_invocation": runs_started,
        "raw_rows_before_dedupe": len(raw_jsonl_rows),
        "raw_rows_after_dedupe": len(raw_rows),
        "expected_rows": len(expected),
        "missing_rows": len(missing),
        "missing_examples": [
            {"map": key[0], "agents": key[1], "seed": key[2], "method": key[3]} for key in missing[:50]
        ],
        "schema_errors": schema_errors,
        "paired_method_stats": stats,
        "by_map_agent_rows": by_group,
        "component_ablation_rows": component_rows,
        "selector_static_audit": selector_static_audit,
        "main_static_sign_test": {
            "better": stats.get(main_method, {}).get("better", 0),
            "worse": stats.get(main_method, {}).get("worse", 0),
        },
        "main_static_worst_group": worst_group,
        "main_static_worst_5_cases": worst_cases,
        "freshness_audit": freshness,
        "mandatory_gates": gates,
        "mandatory_gates_passed": mandatory_gates_passed,
        "interpretation": interpretation,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    write_audit_report(audit_report, summary)
    write_freshness_audit(freshness_audit_report, freshness_audit_json, summary)
    write_decision(decision_report, summary)
    print(
        json.dumps(
            {
                "summary_json": rel(summary_json, root),
                "missing_rows": len(missing),
                "schema_errors": len(schema_errors),
                "mandatory_gates_passed": mandatory_gates_passed,
                "runs_started_this_invocation": runs_started,
            },
            sort_keys=True,
        )
    )
    return 0 if not missing and not schema_errors else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
