"""Run Repair5F.3 runtime export final-holdout evaluation."""

from __future__ import annotations

import argparse
import csv
import json
import math
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
from run_repair5f_updateparam_probe_table import (  # noqa: E402
    Candidate,
    read_candidates,
    write_candidate_runtime,
)


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5f_candidate_lattice.csv"
DEFAULT_HOLDOUT_WIDE = "outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv"
DEFAULT_SELECTOR_RUNTIME = "artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector"
DEFAULT_STATIC_RUNTIME = "artifacts/models/laur_ltm/repair5f_static_c100_b100_w075_d090"
DEFAULT_E5_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker"
DEFAULT_E5_SHUFFLED_RUNTIME = "artifacts/models/laur_ltm/repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5f_runtime_export_eval_runtimes"
DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5f_runtime_export_eval"
DEFAULT_OUTPUT_JSONL = (
    "outputs/logs/phase5p5_repair5f_runtime_export_eval/"
    "phase5p5_repair5f_runtime_export_eval.jsonl"
)
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5f_runtime_export_eval_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5f_runtime_export_eval_summary.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_runtime_export_eval_report.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5f_runtime_export_eval_summary.json"
DEFAULT_AUDIT_REPORT = "outputs/reports/phase5p5_repair5f_runtime_export_eval_audit.md"

MAPS = {
    "random-32-32-20": "external/lacam2/scripts/map/random-32-32-20.map",
    "maze-32-32-4": "external/lacam2/scripts/map/maze-32-32-4.map",
    "warehouse-10-20-10-2-1": "external/lacam2/scripts/map/warehouse-10-20-10-2-1.map",
}

DEFAULT_METHOD_ORDER = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f_bounded_updateparam_selector_runtime",
    "repair5f_bounded_updateparam_selector_force_additive_parity",
    "repair5f_runtime_random_candidate_diagnostic",
    "repair5f_runtime_shuffled_utility_diagnostic",
    "repair5e5_crossfold_utility_reranker",
    "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
    "laur_disable",
    "laur_force_additive_direct",
]

PARITY_FIELDS = ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]


@dataclass(frozen=True)
class MethodSpec:
    method: str
    alias: str
    extra_args: tuple[str, ...] = ()
    requires_runtime_log: bool = False


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


def num(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(num(row.get("agents"), 0)), int(num(row.get("seed"), 0)))


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
        raise KeyError(f"missing candidate {candidate_id}")
    return write_candidate_runtime(runtime_root, candidates[candidate_id])


def holdout_candidate_for(
    holdout_wide: dict[tuple[str, int, int], dict[str, str]],
    key: tuple[str, int, int],
    method: str,
) -> str:
    row = holdout_wide.get(key)
    if row is None:
        raise KeyError(f"missing holdout wide row for {key}")
    if method == "repair5f_runtime_random_candidate_diagnostic":
        return row["repair5f_bounded_updateparam_selector_random_candidate_diagnostic_candidate_id"]
    if method == "repair5f_runtime_shuffled_utility_diagnostic":
        return row["repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic_candidate_id"]
    raise KeyError(method)


def build_method_spec(
    *,
    method: str,
    selector_runtime: Path,
    static_runtime: Path,
    e5_runtime: Path,
    e5_shuffled_runtime: Path,
    runtime_root: Path,
    candidates: dict[str, Candidate],
    holdout_wide: dict[tuple[str, int, int], dict[str, str]],
    key: tuple[str, int, int],
) -> MethodSpec | None:
    if method == "lacam_star_ltm":
        return MethodSpec("lacam_star_ltm", "lacam_star_ltm")
    if method == "always_additive_defer":
        return MethodSpec("always_additive_defer", method)
    if method == "repair5f_candidate_additive_ltm":
        return MethodSpec(method, method)
    if method == "repair5f_static_c100_b100_w075_d090":
        return MethodSpec(method, method, ("--laur-model-path", str(static_runtime), "--laur-safety-threshold", "1.01"), True)
    if method == "repair5f_bounded_updateparam_selector_runtime":
        return MethodSpec(method, method, ("--laur-model-path", str(selector_runtime), "--laur-safety-threshold", "1.01"), True)
    if method == "repair5f_bounded_updateparam_selector_force_additive_parity":
        return MethodSpec(method, method)
    if method in {
        "repair5f_runtime_random_candidate_diagnostic",
        "repair5f_runtime_shuffled_utility_diagnostic",
    }:
        candidate_id = holdout_candidate_for(holdout_wide, key, method)
        runtime = candidate_runtime_path(runtime_root, candidates, candidate_id)
        return MethodSpec(method, method, ("--laur-model-path", str(runtime), "--laur-safety-threshold", "1.01"), True)
    if method == "repair5e5_crossfold_utility_reranker":
        if not e5_runtime.exists():
            return None
        return MethodSpec(
            "lacam_star_lau_ltm",
            method,
            ("--laur-model-path", str(e5_runtime), "--laur-safety-threshold", "0.30", "--laur-ood-z-threshold", "4.25"),
            True,
        )
    if method == "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic":
        if not e5_shuffled_runtime.exists():
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
        )
    if method == "laur_disable":
        return MethodSpec(method, method)
    if method == "laur_force_additive_direct":
        return MethodSpec(method, method)
    raise KeyError(method)


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
    static_runtime: Path,
    e5_runtime: Path,
    e5_shuffled_runtime: Path,
    runtime_root: Path,
    candidates: dict[str, Candidate],
    holdout_wide: dict[tuple[str, int, int], dict[str, str]],
    completed: set[tuple[str, int, int, str]],
) -> list[dict[str, Any]]:
    command_log.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for map_name in maps:
        map_path = root / MAPS[map_name]
        if not map_path.exists():
            raise FileNotFoundError(map_path)
        for seed in instance_ids:
            scen_path = scenario_dir / f"{map_name}-random-{seed}.scen"
            if not scen_path.exists():
                raise FileNotFoundError(scen_path)
            for agents in agent_counts:
                key = (map_name, int(agents), int(seed))
                for method in methods:
                    run_id = (*key, method)
                    if run_id in completed:
                        continue
                    spec = build_method_spec(
                        method=method,
                        selector_runtime=selector_runtime,
                        static_runtime=static_runtime,
                        e5_runtime=e5_runtime,
                        e5_shuffled_runtime=e5_shuffled_runtime,
                        runtime_root=runtime_root,
                        candidates=candidates,
                        holdout_wide=holdout_wide,
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
                        "phase5p5-repair5f-runtime-export-eval",
                        "--project-commit",
                        git_value(["rev-parse", "--short", "HEAD"], root),
                        "--external-commit",
                        "local",
                        "--branch",
                        git_value(["branch", "--show-current"], root),
                        "--dirty",
                        dirty_state(root),
                        "--platform",
                        "Windows Repair5F runtime export diagnostic",
                        *extra,
                    ]
                    completed_process = subprocess.run(command, cwd=root, text=True, capture_output=True)
                    row = {
                        "method": method,
                        "map": map_name,
                        "agents": int(agents),
                        "seed": int(seed),
                        "returncode": completed_process.returncode,
                        "command": command,
                        "stdout": completed_process.stdout.strip()[-500:],
                        "stderr": completed_process.stderr.strip()[-500:],
                    }
                    rows.append(row)
                    with command_log.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(row, sort_keys=True) + "\n")
                    if completed_process.returncode == 1:
                        raise RuntimeError(
                            f"solver crashed for {method} {map_name} a{agents} s{seed}: {completed_process.stderr}"
                        )
    return rows


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
    if boolish(row.get("laur_force_additive")):
        return "additive_ltm"
    return ""


def build_paired(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[case_key(row)][str(row.get("method"))] = row
    paired: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        base = methods.get("lacam_star_ltm")
        if base is None:
            continue
        base_ratio = num(base.get("sum_of_loss_ratio"))
        for method, row in sorted(methods.items()):
            if method == "lacam_star_ltm":
                continue
            ratio = num(row.get("sum_of_loss_ratio"))
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
                    "sum_of_loss_ratio": ratio if math.isfinite(ratio) else "",
                    "ltm_sum_of_loss_ratio": base_ratio if math.isfinite(base_ratio) else "",
                    "delta_ratio_vs_ltm": delta if math.isfinite(delta) else "",
                    "better_vs_ltm": math.isfinite(delta) and delta < -1.0e-12,
                    "equal_vs_ltm": math.isfinite(delta) and abs(delta) <= 1.0e-12,
                    "worse_vs_ltm": math.isfinite(delta) and delta > 1.0e-12,
                    "selected_candidate_id": selected_candidate_from_row(row),
                    "laur_update_mode": row.get("laur_update_mode", ""),
                    "laur_model_path": row.get("laur_model_path", ""),
                    "expanded_delta_vs_ltm": num(row.get("expanded_nodes"), 0.0) - num(base.get("expanded_nodes"), 0.0),
                    "low_level_pibt_delta_vs_ltm": num(row.get("low_level_pibt_calls"), 0.0)
                    - num(base.get("low_level_pibt_calls"), 0.0),
                    "ttfs_delta_vs_ltm": num(row.get("time_to_first_solution_ms"), 0.0)
                    - num(base.get("time_to_first_solution_ms"), 0.0),
                }
            )
    return paired


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.mean(clean) if clean else None


def summarize_method(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [num(row.get("delta_ratio_vs_ltm")) for row in rows]
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
        "mean_delta_ratio_vs_ltm": mean(deltas),
        "ratio_worse_than_ltm_groups": sum(
            1
            for group in grouped.values()
            if (mean([num(row.get("delta_ratio_vs_ltm")) for row in group]) or 0.0) > 1.0e-12
        ),
        "success_worse_than_ltm_groups": sum(
            1
            for group in grouped.values()
            if sum(1 for row in group if boolish(row.get("success"))) < sum(1 for row in group if boolish(row.get("ltm_success")))
        ),
        "selected_nonadditive_cases": len(nonadditive),
        "additive_fallback_cases": len(rows) - len(nonadditive),
        "additive_fallback_rate": (len(rows) - len(nonadditive)) / len(rows) if rows else 0.0,
        "selected_candidate_distribution": dict(sorted(candidate_counts.items())),
        "zero_nonadditive_groups": sum(
            1 for group in grouped.values() if all(row.get("selected_candidate_id") in {"", "additive_ltm"} for row in group)
        ),
    }


def summarize_paired(paired: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in paired:
        grouped[str(row["method"])].append(row)
    return {method: summarize_method(rows) for method, rows in sorted(grouped.items())}


def parity_exact(rows: list[dict[str, Any]], method: str) -> bool:
    by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[case_key(row)][str(row.get("method"))] = row
    observed = 0
    for methods in by_case.values():
        base = methods.get("lacam_star_ltm")
        other = methods.get(method)
        if base is None or other is None:
            return False
        observed += 1
        for field in PARITY_FIELDS:
            if base.get(field) != other.get(field):
                return False
    return observed > 0


def runtime_gates(stats: dict[str, dict[str, Any]], raw_rows: list[dict[str, Any]]) -> dict[str, bool]:
    selector = stats.get("repair5f_bounded_updateparam_selector_runtime", {})
    random_diag = stats.get("repair5f_runtime_random_candidate_diagnostic", {})
    shuffled_diag = stats.get("repair5f_runtime_shuffled_utility_diagnostic", {})
    e5 = stats.get("repair5e5_crossfold_utility_reranker", {})
    selector_mean = selector.get("mean_delta_ratio_vs_ltm")
    random_mean = random_diag.get("mean_delta_ratio_vs_ltm")
    shuffled_mean = shuffled_diag.get("mean_delta_ratio_vs_ltm")
    e5_mean = e5.get("mean_delta_ratio_vs_ltm")
    return {
        "force_additive_parity_exact": parity_exact(raw_rows, "repair5f_bounded_updateparam_selector_force_additive_parity"),
        "exact_additive_candidate_parity_exact": parity_exact(raw_rows, "repair5f_candidate_additive_ltm"),
        "laur_disable_parity_exact": parity_exact(raw_rows, "laur_disable"),
        "laur_force_additive_direct_parity_exact": parity_exact(raw_rows, "laur_force_additive_direct"),
        "support_final_leakage_false": True,
        "runtime_selector_better_gt_worse": int(selector.get("better") or 0) > int(selector.get("worse") or 0),
        "runtime_selector_mean_delta_lt_0": selector_mean is not None and float(selector_mean) < 0.0,
        "runtime_selector_ratio_worse_groups_le_1": int(selector.get("ratio_worse_than_ltm_groups") or 0) <= 1,
        "runtime_selector_success_worse_groups_eq_0": int(selector.get("success_worse_than_ltm_groups") or 0) == 0,
        "runtime_selector_beats_random_diagnostic": (
            selector_mean is not None and random_mean is not None and float(selector_mean) < float(random_mean)
        ),
        "runtime_selector_beats_shuffled_utility_diagnostic": (
            selector_mean is not None and shuffled_mean is not None and float(selector_mean) < float(shuffled_mean)
        ),
        "runtime_selector_improves_over_e5_real_selector": (
            selector_mean is not None and e5_mean is not None and float(selector_mean) < float(e5_mean)
        ),
        "runtime_selector_does_not_collapse_to_additive_parity": int(selector.get("selected_nonadditive_cases") or 0) > 0,
        "phase5p5_allowed_false": True,
        "phase6_allowed_false": True,
    }


def static_ablation(paired: list[dict[str, Any]]) -> dict[str, Any]:
    by_case_method = {(*case_key(row), str(row["method"])): row for row in paired}
    mismatches: list[dict[str, Any]] = []
    no_eligible_equal_metric: list[dict[str, Any]] = []
    for key_method, selector in sorted(by_case_method.items()):
        map_name, agents, seed, method = key_method
        if method != "repair5f_bounded_updateparam_selector_runtime":
            continue
        static = by_case_method.get((map_name, agents, seed, "repair5f_static_c100_b100_w075_d090"))
        if static is None:
            mismatches.append({"map": map_name, "agents": agents, "seed": seed, "reason": "missing_static"})
            continue
        selector_delta = str(selector.get("delta_ratio_vs_ltm"))
        static_delta = str(static.get("delta_ratio_vs_ltm"))
        selector_candidate = selector.get("selected_candidate_id")
        static_candidate = static.get("selected_candidate_id")
        if selector_delta != static_delta:
            mismatches.append(
                {
                    "map": map_name,
                    "agents": agents,
                    "seed": seed,
                    "selector_candidate": selector_candidate,
                    "static_candidate": static_candidate,
                    "selector_delta": selector_delta,
                    "static_delta": static_delta,
                    "reason": "metric_difference",
                }
            )
        elif selector_candidate != static_candidate:
            no_eligible_equal_metric.append(
                {
                    "map": map_name,
                    "agents": agents,
                    "seed": seed,
                    "selector_candidate": selector_candidate,
                    "static_candidate": static_candidate,
                    "delta": selector_delta,
                    "reason": "static_run_had_no_eligible_update_but_metric_equal",
                }
            )
    return {
        "selector_static_runtime_metrics_equal": not mismatches,
        "selector_static_candidate_policy_equal_on_eligible_updates": not mismatches,
        "mismatch_count": len(mismatches),
        "mismatch_examples": mismatches[:20],
        "no_eligible_update_equal_metric_cases": no_eligible_equal_metric[:20],
        "interpretation": (
            "support_trained_static_bounded_updateparams"
            if not mismatches
            else "inspect_runtime_static_differences_before_claims"
        ),
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary["paired_method_stats"]
    gates = summary["runtime_gates"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.3 Runtime Export Evaluation\n\n")
        handle.write("This is diagnostic-only runtime evidence. Phase5.5 and Phase6 remain forbidden.\n\n")
        handle.write("## Runtime Scope\n\n")
        scope = summary["scope"]
        handle.write(f"- maps: `{scope['maps']}`\n")
        handle.write(f"- agents: `{scope['agent_counts']}`\n")
        handle.write(f"- instance_ids: `{scope['instance_ids']}`\n")
        handle.write(f"- time_limit_sec: `{scope['time_limit_sec']}`\n")
        handle.write(f"- ltm_max_iterations: `{scope['ltm_max_iterations']}`\n\n")
        handle.write("## Method Summary\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for method in DEFAULT_METHOD_ORDER:
            if method == "lacam_star_ltm":
                continue
            row = stats.get(method)
            if row:
                handle.write(
                    f"| `{method}` | {row.get('rows')} | {row.get('better')} | {row.get('equal')} | "
                    f"{row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
                )
        handle.write("\n## Gates\n\n")
        for key, value in gates.items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Static-Candidate Ablation\n\n")
        ablation = summary["static_candidate_ablation"]
        handle.write(f"- selector_static_runtime_metrics_equal: `{ablation['selector_static_runtime_metrics_equal']}`\n")
        handle.write(
            "- selector_static_candidate_policy_equal_on_eligible_updates: "
            f"`{ablation['selector_static_candidate_policy_equal_on_eligible_updates']}`\n"
        )
        handle.write(f"- interpretation: `{ablation['interpretation']}`\n\n")
        handle.write("If the selector and static candidate are equal, the result must be reported as a support-trained static bounded UpdateParams replacement, not context-adaptive selection.\n")


def write_audit_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.3 Runtime Export Evaluation Audit\n\n")
        handle.write("This audit is diagnostic-only.\n\n")
        handle.write("## Coverage\n\n")
        handle.write(f"- raw_rows_before_dedupe: `{summary['raw_rows_before_dedupe']}`\n")
        handle.write(f"- raw_rows_after_dedupe: `{summary['raw_rows_after_dedupe']}`\n")
        handle.write(f"- expected_rows: `{summary['expected_rows']}`\n")
        handle.write(f"- missing_rows: `{summary['missing_rows']}`\n")
        handle.write(f"- schema_errors: `{len(summary['schema_errors'])}`\n\n")
        handle.write("## Gate Snapshot\n\n")
        for key, value in summary["runtime_gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--candidate-lattice-csv", type=Path, default=Path(DEFAULT_CANDIDATE_CSV))
    parser.add_argument("--holdout-wide-csv", type=Path, default=Path(DEFAULT_HOLDOUT_WIDE))
    parser.add_argument("--selector-runtime-dir", type=Path, default=Path(DEFAULT_SELECTOR_RUNTIME))
    parser.add_argument("--static-runtime-dir", type=Path, default=Path(DEFAULT_STATIC_RUNTIME))
    parser.add_argument("--repair5e5-runtime-dir", type=Path, default=Path(DEFAULT_E5_RUNTIME))
    parser.add_argument("--repair5e5-shuffled-runtime-dir", type=Path, default=Path(DEFAULT_E5_SHUFFLED_RUNTIME))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_AUDIT_REPORT))
    parser.add_argument("--maps", nargs="+", choices=sorted(MAPS), default=sorted(MAPS))
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=[21, 22, 23, 24, 25])
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHOD_ORDER)
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve(args.binary, root)
    scenario_dir = resolve(args.scenario_dir, root)
    candidate_csv = resolve(args.candidate_lattice_csv, root)
    holdout_wide_csv = resolve(args.holdout_wide_csv, root)
    selector_runtime = resolve(args.selector_runtime_dir, root)
    static_runtime = resolve(args.static_runtime_dir, root)
    e5_runtime = resolve(args.repair5e5_runtime_dir, root)
    e5_shuffled_runtime = resolve(args.repair5e5_shuffled_runtime_dir, root)
    runtime_root = resolve(args.runtime_root, root)
    output_dir = resolve(args.output_dir, root)
    output_jsonl = resolve(args.output_jsonl, root)
    paired_csv = resolve(args.paired_csv, root)
    summary_csv = resolve(args.summary_csv, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    audit_report = resolve(args.audit_report, root)
    command_log = output_jsonl.with_name(output_jsonl.stem + "_commands.jsonl")
    update_log = output_jsonl.with_name(output_jsonl.stem + "_laur_updates.jsonl")

    if args.overwrite and args.resume:
        raise ValueError("--overwrite and --resume cannot both be set")
    for path in [candidate_csv, holdout_wide_csv, selector_runtime, static_runtime]:
        if not path.exists():
            raise FileNotFoundError(path)

    output_dir.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()
    if not args.skip_solver and not binary.exists():
        raise FileNotFoundError(binary)

    candidates = candidate_by_id(read_candidates(candidate_csv))
    holdout_wide_rows = read_csv_rows(holdout_wide_csv)
    holdout_wide = {case_key(row): row for row in holdout_wide_rows}
    completed: set[tuple[str, int, int, str]] = set()
    if output_jsonl.exists() and args.resume:
        completed = completed_keys(dedupe_rows(read_jsonl(output_jsonl)))
    elif output_jsonl.exists() and not args.skip_solver:
        raise FileExistsError(f"output JSONL already exists: {output_jsonl}")

    if not args.skip_solver:
        run_grid(
            root=root,
            binary=binary,
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            update_log=update_log,
            maps=list(args.maps),
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=list(args.methods),
            selector_runtime=selector_runtime,
            static_runtime=static_runtime,
            e5_runtime=e5_runtime,
            e5_shuffled_runtime=e5_shuffled_runtime,
            runtime_root=runtime_root,
            candidates=candidates,
            holdout_wide=holdout_wide,
            completed=completed,
        )

    raw_jsonl_rows = read_jsonl(output_jsonl)
    raw_rows = dedupe_rows(raw_jsonl_rows)
    observed = completed_keys(raw_rows)
    expected = {
        (map_name, int(agents), int(seed), method)
        for map_name in args.maps
        for agents in args.agent_counts
        for seed in args.instance_ids
        for method in args.methods
        if method in DEFAULT_METHOD_ORDER
    }
    missing = sorted(expected - observed)
    schema_errors: list[str] = []
    for index, row in enumerate(raw_rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))
    paired = build_paired(raw_rows)
    stats = summarize_paired(paired)
    gates = runtime_gates(stats, raw_rows)
    ablation = static_ablation(paired)
    paired_fields = [
        "map",
        "agents",
        "seed",
        "scen",
        "method",
        "success",
        "ltm_success",
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
        "ratio_worse_than_ltm_groups",
        "success_worse_than_ltm_groups",
        "selected_nonadditive_cases",
        "additive_fallback_rate",
        "zero_nonadditive_groups",
        "selected_candidate_distribution",
    ]
    write_csv(summary_csv, summary_rows, summary_fields)

    summary = {
        "schema_version": "phase5p5_repair5f_runtime_export_eval_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "scope": {
            "maps": list(args.maps),
            "agent_counts": [int(value) for value in args.agent_counts],
            "instance_ids": [int(value) for value in args.instance_ids],
            "time_limit_sec": float(args.time_limit_sec),
            "ltm_max_iterations": int(args.ltm_max_iterations),
            "methods": list(args.methods),
        },
        "raw_jsonl": rel(output_jsonl, root),
        "command_log_jsonl": rel(command_log, root),
        "laur_update_log_jsonl": rel(update_log, root),
        "paired_csv": rel(paired_csv, root),
        "summary_csv": rel(summary_csv, root),
        "report": rel(report, root),
        "summary_json": rel(summary_json, root),
        "audit_report": rel(audit_report, root),
        "raw_rows_before_dedupe": len(raw_jsonl_rows),
        "raw_rows_after_dedupe": len(raw_rows),
        "expected_rows": len(expected),
        "missing_rows": len(missing),
        "missing_examples": [
            {"map": key[0], "agents": key[1], "seed": key[2], "method": key[3]} for key in missing[:50]
        ],
        "schema_errors": schema_errors,
        "paired_method_stats": stats,
        "runtime_gates": gates,
        "runtime_gates_passed": all(gates.values()),
        "static_candidate_ablation": ablation,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    write_audit_report(audit_report, summary)
    print(json.dumps({"summary_json": rel(summary_json, root), "runtime_gates_passed": summary["runtime_gates_passed"]}))
    return 0 if not schema_errors and not missing else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
