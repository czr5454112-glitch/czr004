"""Shared helpers for Repair5G.2 flow-shield selector diagnostics."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402
from run_repair5f4_static_updateparams_validation import (  # noqa: E402
    MAPS,
    audit_and_prepare_scenarios,
    scenario_path,
)
from run_repair5g_dual_channel_probe import (  # noqa: E402
    MethodSpec,
    case_key,
    finite,
    make_f4_best_runtime,
    method_parity_exact,
    row_score,
    run_key,
    schema_error_count,
)


BASELINE_METHOD = "lacam_star_ltm"
G2_RANDOM_DIAGNOSTIC = "repair5g2_random_candidate_diagnostic"
G2_SHUFFLED_GOAL_DIAGNOSTIC = "repair5g2_shuffled_goal_progress_diagnostic"
G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC = "repair5g2_shuffled_flow_shield_diagnostic"
G2_SYNTHETIC_DIAGNOSTICS = [
    G2_RANDOM_DIAGNOSTIC,
    G2_SHUFFLED_GOAL_DIAGNOSTIC,
    G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC,
]

PARITY_FIELDS = ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]


@dataclass(frozen=True)
class SelectorDecision:
    map: str
    agents: int
    seed: int
    selected_method: str
    selector_alias: str
    selector_type: str
    fallback_reason: str = ""
    selected_source: str = ""


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


def now_iso() -> str:
    return datetime.now().isoformat()


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
    clean = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.mean(clean) if clean else None


def median(values: list[float]) -> float | None:
    clean = [float(value) for value in values if math.isfinite(float(value))]
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


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


def map_family(map_name: str) -> str:
    return str(map_name).split("-", 1)[0]


def map_defaults(map_name: str, agents: int) -> dict[str, float]:
    parts = str(map_name).split("-")
    width = number(parts[1] if len(parts) > 2 else "", 0.0)
    height = number(parts[2] if len(parts) > 2 else "", 0.0)
    obstacle_ratio = 0.0
    if str(map_name).startswith("random-") and len(parts) >= 4:
        obstacle_ratio = number(parts[3], 0.0) / 100.0
    if str(map_name).startswith("warehouse-"):
        width = number(parts[2] if len(parts) > 2 else "", 0.0)
        height = number(parts[1] if len(parts) > 1 else "", 0.0)
        obstacle_ratio = 0.0
    free_cells = max(width * height * (1.0 - obstacle_ratio), 0.0)
    return {
        "map_width": width,
        "map_height": height,
        "obstacle_ratio": obstacle_ratio,
        "free_cells": free_cells,
        "density": (float(agents) / free_cells) if free_cells > 0 else 0.0,
    }


def subset_component_map(subset_rows: list[dict[str, Any]]) -> dict[str, str]:
    return {str(row["runtime_method"]): str(row.get("component", "")) for row in subset_rows}


def actual_subset_rows(subset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in subset_rows:
        if boolish(row.get("synthetic_diagnostic")):
            continue
        if not boolish(row.get("include_in_solver", True)):
            continue
        out.append(row)
    return out


def method_specs_from_subset(subset_rows: list[dict[str, Any]], runtime_root: Path) -> list[MethodSpec]:
    root = repo_root()
    specs: list[MethodSpec] = []
    seen: set[str] = set()
    f4_runtime = make_f4_best_runtime(runtime_root / "repair5f4_best_static")
    for row in actual_subset_rows(subset_rows):
        alias = str(row["runtime_method"])
        if alias in seen:
            continue
        seen.add(alias)
        component = str(row.get("component", ""))
        candidate_id = str(row.get("candidate_id", ""))
        if alias == "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only":
            specs.append(
                MethodSpec(
                    "lacam_star_lau_ltm",
                    alias,
                    ("--laur-model-path", str(f4_runtime), "--laur-safety-threshold", "1.01"),
                    component=component or "repair5f_c_only",
                    candidate_id=candidate_id or "c125_b125_w075_d095",
                )
            )
        else:
            specs.append(MethodSpec(alias, alias, (), component=component, candidate_id=candidate_id))
    _ = root
    return specs


def expected_keys(
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    methods: list[str],
) -> set[tuple[str, int, int, str]]:
    return {
        (map_name, int(agents), int(seed), method)
        for map_name in maps
        for agents in agent_counts
        for seed in instance_ids
        for method in methods
    }


def row_by_case_method(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    return {
        (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("method"))): row
        for row in rows
    }


def case_dict(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(case_key(row), {})[str(row.get("method"))] = row
    return grouped


def candidate_methods_from_subset(subset_rows: list[dict[str, Any]], *, include_c_equiv: bool = True) -> list[str]:
    methods: list[str] = []
    for row in actual_subset_rows(subset_rows):
        component = str(row.get("component", ""))
        method = str(row["runtime_method"])
        if component == "control":
            continue
        if component == "c_equiv_baseline" and not include_c_equiv:
            continue
        if method == BASELINE_METHOD:
            continue
        methods.append(method)
    return sorted(dict.fromkeys(methods))


def synthesize_g2_diagnostics(rows: list[dict[str, Any]], subset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_candidates = candidate_methods_from_subset(subset_rows)
    flow_candidates = sorted(
        str(row["runtime_method"])
        for row in actual_subset_rows(subset_rows)
        if str(row.get("component")) == "flow_shield"
    )
    grouped = case_dict(rows)
    ordered_cases = sorted(grouped)
    if not all_candidates:
        return []
    best_by_case: dict[tuple[str, int, int, str], str] = {}
    best_flow_by_case: dict[tuple[str, int, int, str], str] = {}
    for key in ordered_cases:
        methods = grouped[key]
        present = [methods[method] for method in all_candidates if method in methods]
        if present:
            best_by_case[key] = str(min(present, key=row_score).get("method"))
        flow_present = [methods[method] for method in flow_candidates if method in methods]
        if flow_present:
            best_flow_by_case[key] = str(min(flow_present, key=row_score).get("method"))

    out: list[dict[str, Any]] = []
    for index, key in enumerate(ordered_cases):
        methods = grouped[key]
        digest = hashlib.sha256(repr(key).encode("utf-8")).hexdigest()
        random_source = all_candidates[int(digest[:12], 16) % len(all_candidates)]
        if random_source in methods:
            row = dict(methods[random_source])
            row["method"] = G2_RANDOM_DIAGNOSTIC
            row["repair5g2_synthetic_source_method"] = random_source
            out.append(row)

        next_key = ordered_cases[(index + 1) % len(ordered_cases)] if ordered_cases else key
        shuffled_source = best_by_case.get(next_key, random_source)
        if shuffled_source in methods:
            row = dict(methods[shuffled_source])
            row["method"] = G2_SHUFFLED_GOAL_DIAGNOSTIC
            row["repair5g2_synthetic_source_method"] = shuffled_source
            out.append(row)

        flow_source = best_flow_by_case.get(next_key, "")
        if flow_source in methods:
            row = dict(methods[flow_source])
            row["method"] = G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC
            row["repair5g2_synthetic_source_method"] = flow_source
            out.append(row)
    return out


def synthesize_selector_rows(rows: list[dict[str, Any]], decisions: list[SelectorDecision]) -> list[dict[str, Any]]:
    by_key = row_by_case_method(rows)
    out: list[dict[str, Any]] = []
    for decision in decisions:
        key = (decision.map, int(decision.agents), int(decision.seed), decision.selected_method)
        source = by_key.get(key)
        if source is None:
            continue
        row = dict(source)
        row["method"] = decision.selector_alias
        row["repair5g2_selector_type"] = decision.selector_type
        row["repair5g2_selected_source_method"] = decision.selected_method
        row["repair5g2_selected_source"] = decision.selected_source
        row["repair5g2_fallback_reason"] = decision.fallback_reason
        out.append(row)
    return out


def build_utility_long(rows: list[dict[str, Any]], component_by_method: dict[str, str]) -> list[dict[str, Any]]:
    grouped = case_dict(rows)
    out: list[dict[str, Any]] = []
    for key, methods in sorted(grouped.items()):
        baseline = methods.get(BASELINE_METHOD)
        if baseline is None:
            continue
        base_ratio = finite(baseline.get("sum_of_loss_ratio"))
        baseline_success = bool(baseline.get("success"))
        for method, contender in sorted(methods.items()):
            if method == BASELINE_METHOD:
                continue
            ratio = finite(contender.get("sum_of_loss_ratio"))
            delta = ratio - base_ratio if math.isfinite(ratio) and math.isfinite(base_ratio) else None
            contender_success = bool(contender.get("success"))
            out.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "candidate_id": method,
                    "contender_method": method,
                    "component": component_by_method.get(method, "synthetic"),
                    "baseline_method": BASELINE_METHOD,
                    "baseline_success": baseline_success,
                    "success": contender_success,
                    "baseline_ratio": base_ratio if math.isfinite(base_ratio) else None,
                    "sum_of_loss_ratio": ratio if math.isfinite(ratio) else None,
                    "delta_ratio_vs_ltm": delta,
                    "better_vs_ltm": contender_success and ((not baseline_success) or (delta is not None and delta < -1.0e-12)),
                    "equal_vs_ltm": delta is not None and abs(delta) <= 1.0e-12 and contender_success == baseline_success,
                    "worse_vs_ltm": baseline_success and ((not contender_success) or (delta is not None and delta > 1.0e-12)),
                    "repair5g2_synthetic_source_method": contender.get("repair5g2_synthetic_source_method", ""),
                    "repair5g2_selected_source_method": contender.get("repair5g2_selected_source_method", ""),
                }
            )
    return out


def build_wide_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = case_dict(rows)
    out: list[dict[str, Any]] = []
    for key, methods in sorted(grouped.items()):
        base_ratio = finite(methods.get(BASELINE_METHOD, {}).get("sum_of_loss_ratio"))
        row: dict[str, Any] = {"map": key[0], "agents": key[1], "seed": key[2], "scen": key[3]}
        for method, source in sorted(methods.items()):
            ratio = finite(source.get("sum_of_loss_ratio"))
            row[f"{method}_success"] = source.get("success")
            row[f"{method}_ratio"] = ratio if math.isfinite(ratio) else None
            row[f"{method}_delta_ratio_vs_ltm"] = (
                ratio - base_ratio
                if method != BASELINE_METHOD and math.isfinite(ratio) and math.isfinite(base_ratio)
                else None
            )
        out.append(row)
    return out


def method_stats_from_long(long_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in long_rows:
        grouped.setdefault(str(row["candidate_id"]), []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for method, group in sorted(grouped.items()):
        deltas = [number(row.get("delta_ratio_vs_ltm")) for row in group]
        out[method] = {
            "method": method,
            "rows": len(group),
            "better": sum(1 for row in group if boolish(row.get("better_vs_ltm"))),
            "equal": sum(1 for row in group if boolish(row.get("equal_vs_ltm"))),
            "worse": sum(1 for row in group if boolish(row.get("worse_vs_ltm"))),
            "mean_delta_ratio_vs_ltm": mean(deltas),
        }
    return out


def by_map_agent_rows(long_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for row in long_rows:
        key = (str(row["map"]), int(number(row["agents"], 0)), str(row["candidate_id"]))
        grouped.setdefault(key, []).append(row)
    out: list[dict[str, Any]] = []
    for (map_name, agents, method), group in sorted(grouped.items()):
        deltas = [number(row.get("delta_ratio_vs_ltm")) for row in group]
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "method": method,
                "rows": len(group),
                "better": sum(1 for row in group if boolish(row.get("better_vs_ltm"))),
                "equal": sum(1 for row in group if boolish(row.get("equal_vs_ltm"))),
                "worse": sum(1 for row in group if boolish(row.get("worse_vs_ltm"))),
                "mean_delta_ratio_vs_ltm": mean(deltas),
            }
        )
    return out


def bootstrap_summary(values: list[float], *, samples: int = 2000, seed: int = 20260603) -> dict[str, Any]:
    clean = [value for value in values if math.isfinite(value)]
    if not clean:
        return {"mean": None, "ci_low": None, "ci_high": None, "prob_mean_lt_0": None, "samples": 0}
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(samples):
        draw = [clean[rng.randrange(len(clean))] for _ in clean]
        means.append(statistics.mean(draw))
    means.sort()
    return {
        "mean": statistics.mean(clean),
        "ci_low": means[int(0.025 * (len(means) - 1))],
        "ci_high": means[int(0.975 * (len(means) - 1))],
        "prob_mean_lt_0": sum(1 for value in means if value < 0.0) / len(means),
        "samples": len(means),
    }


def metrics_for_long_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [number(row.get("delta_ratio_vs_ltm")) for row in rows]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["map"]), int(number(row["agents"], 0))), []).append(row)
    candidate_counts: dict[str, int] = {}
    for row in rows:
        candidate_counts[str(row.get("candidate_id", ""))] = candidate_counts.get(str(row.get("candidate_id", "")), 0) + 1
    return {
        "rows": len(rows),
        "better": sum(1 for value in deltas if value < -1.0e-12),
        "equal": sum(1 for value in deltas if math.isfinite(value) and abs(value) <= 1.0e-12),
        "worse": sum(1 for value in deltas if value > 1.0e-12),
        "mean_delta_ratio_vs_ltm": mean(deltas),
        "median_delta_ratio_vs_ltm": median(deltas),
        "bootstrap": bootstrap_summary(deltas),
        "ratio_worse_than_ltm_groups": sum(
            1
            for group in grouped.values()
            if (mean([number(row.get("delta_ratio_vs_ltm")) for row in group]) or 0.0) > 1.0e-12
        ),
        "success_worse_than_ltm_groups": 0,
        "selected_candidate_distribution": dict(sorted(candidate_counts.items())),
    }


def parity_mismatch_rows(rows: list[dict[str, Any]], pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    grouped = case_dict(rows)
    out: list[dict[str, Any]] = []
    for key, methods in sorted(grouped.items()):
        for left_method, right_method in pairs:
            left = methods.get(left_method)
            right = methods.get(right_method)
            if left is None or right is None:
                out.append(
                    {
                        "map": key[0],
                        "agents": key[1],
                        "seed": key[2],
                        "scen": key[3],
                        "left_method": left_method,
                        "right_method": right_method,
                        "classification": "missing_row",
                        "mismatched_fields": "missing_row",
                    }
                )
                continue
            mismatched = [field for field in PARITY_FIELDS if left.get(field) != right.get(field)]
            if not mismatched:
                continue
            left_runtime = number(left.get("runtime_ms"), 0.0)
            right_runtime = number(right.get("runtime_ms"), 0.0)
            time_limit = max(number(left.get("time_limit_sec"), 0.0), number(right.get("time_limit_sec"), 0.0)) * 1000.0
            near_budget = time_limit > 0.0 and max(left_runtime, right_runtime) >= 0.85 * time_limit
            classification = "time_budget_sensitivity" if near_budget else "true_semantic_mismatch"
            out.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "left_method": left_method,
                    "right_method": right_method,
                    "classification": classification,
                    "mismatched_fields": ",".join(mismatched),
                    "left_ratio": left.get("sum_of_loss_ratio"),
                    "right_ratio": right.get("sum_of_loss_ratio"),
                    "left_success": left.get("success"),
                    "right_success": right.get("success"),
                    "left_runtime_ms": left_runtime,
                    "right_runtime_ms": right_runtime,
                    "time_limit_ms": time_limit,
                }
            )
    return out


def method_pair_exact(rows: list[dict[str, Any]], left_method: str, right_method: str) -> bool:
    grouped = case_dict(rows)
    checked = 0
    for methods in grouped.values():
        left = methods.get(left_method)
        right = methods.get(right_method)
        if left is None or right is None:
            continue
        checked += 1
        for field in PARITY_FIELDS:
            if left.get(field) != right.get(field):
                return False
    return checked > 0


def write_update_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            method = str(row.get("method", ""))
            if not (method.startswith("repair5g") or method.startswith("repair5g2")):
                continue
            handle.write(
                json.dumps(
                    {
                        "schema_version": "phase5p5_repair5g2_ltm_update_summary_v1",
                        "method": row.get("method"),
                        "map": row.get("map"),
                        "agents": row.get("agents"),
                        "seed": row.get("seed"),
                        "repair5g_candidate_id": row.get("repair5g_candidate_id"),
                        "dual_channel_enabled": row.get("dual_channel_enabled"),
                        "repair5g_update_mode": row.get("repair5g_update_mode"),
                        "repair5g_goal_projection_mode": row.get("repair5g_goal_projection_mode"),
                        "repair5g_congestion_update_count": row.get("repair5g_congestion_update_count"),
                        "repair5g_flow_update_count": row.get("repair5g_flow_update_count"),
                        "repair5g_congestion_nonzero_edges": row.get("repair5g_congestion_nonzero_edges"),
                        "repair5g_flow_nonzero_edges": row.get("repair5g_flow_nonzero_edges"),
                        "repair5g_cost_bounds_respected": row.get("repair5g_cost_bounds_respected"),
                        "repair5g2_synthetic_source_method": row.get("repair5g2_synthetic_source_method", ""),
                        "repair5g2_selected_source_method": row.get("repair5g2_selected_source_method", ""),
                    },
                    sort_keys=True,
                )
                + "\n"
            )


def run_one_solver_task(
    *,
    root: Path,
    binary: Path,
    scenario_dir: Path,
    temp_dir: Path,
    map_name: str,
    agents: int,
    seed: int,
    time_limit_sec: float,
    ltm_max_iterations: int,
    spec: MethodSpec,
    manifest: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    map_path = root / MAPS[map_name]
    scen_path = scenario_path(scenario_dir, map_name, seed)
    if not map_path.exists():
        raise FileNotFoundError(map_path)
    if not scen_path.exists():
        raise FileNotFoundError(scen_path)
    digest = hashlib.sha256(f"{map_name}|{agents}|{seed}|{spec.alias}".encode("utf-8")).hexdigest()[:16]
    task_jsonl = temp_dir / f"{digest}.jsonl"
    task_update = temp_dir / f"{digest}.updates.jsonl"
    if task_jsonl.exists():
        task_jsonl.unlink()
    if task_update.exists():
        task_update.unlink()
    extra_args = list(spec.extra_args)
    if spec.method == "lacam_star_lau_ltm":
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
        "Windows Repair5G.2 flow-shield selector diagnostic",
        *extra_args,
    ]
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True)
    command_row = {
        "method": spec.alias,
        "map": map_name,
        "agents": int(agents),
        "seed": int(seed),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip()[-500:],
        "stderr": completed.stderr.strip()[-500:],
        "command": command,
    }
    rows = read_jsonl(task_jsonl)
    try:
        task_jsonl.unlink(missing_ok=True)
        task_update.unlink(missing_ok=True)
    except TypeError:  # pragma: no cover - Python <3.8 guard
        if task_jsonl.exists():
            task_jsonl.unlink()
        if task_update.exists():
            task_update.unlink()
    if completed.returncode == 1:
        raise RuntimeError(
            f"solver crashed for {spec.alias} {map_name} a{agents} i{seed}: {completed.stderr}"
        )
    return rows, command_row


def run_solver_grid(
    *,
    root: Path,
    binary: Path,
    scenario_dir: Path,
    output_jsonl: Path,
    command_log: Path,
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
    command_log.parent.mkdir(parents=True, exist_ok=True)
    tasks: list[tuple[str, int, int, MethodSpec]] = []
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

    def submit_task(item: tuple[str, int, int, MethodSpec]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        map_name, agents, seed, spec = item
        return run_one_solver_task(
            root=root,
            binary=binary,
            scenario_dir=scenario_dir,
            temp_dir=temp_dir,
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
            rows, command_row = future.result()
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
                            "created_at": now_iso(),
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


def support_gate_summary(rows: list[dict[str, Any]], *, include_static_c_equiv_pairs: bool = True) -> dict[str, Any]:
    gates = {
        "additive_parity_exact": method_parity_exact(rows, "repair5f_candidate_additive_ltm"),
        "always_additive_defer_parity_exact": method_parity_exact(rows, "always_additive_defer"),
        "laur_disable_parity_exact": method_parity_exact(rows, "laur_disable"),
        "laur_force_additive_direct_parity_exact": method_parity_exact(rows, "laur_force_additive_direct"),
        "dual_additive_parity_exact": method_parity_exact(rows, "repair5g_dual_additive_parity"),
        "dual_c_equiv_additive_parity_exact": method_parity_exact(rows, "repair5g_dual_c_equiv_additive"),
        "all_costs_finite": all(
            bool(row.get("repair5g_costs_finite", True))
            for row in rows
            if str(row.get("method", "")).startswith(("repair5g", "repair5g1", "repair5g2"))
        ),
        "cost_bounds_respected": all(
            bool(row.get("repair5g_cost_bounds_respected", True))
            for row in rows
            if str(row.get("method", "")).startswith(("repair5g", "repair5g1", "repair5g2"))
        ),
    }
    if include_static_c_equiv_pairs:
        gates.update(
            {
                "dual_c_equiv_locked_matches_scalar": method_pair_exact(
                    rows,
                    "repair5f_static_c100_b100_w075_d090",
                    "repair5g_dual_c_equiv_c100_b100_w075_d090",
                ),
                "dual_c_equiv_best_f4_static_matches_scalar": method_pair_exact(
                    rows,
                    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
                    "repair5g_dual_c_equiv_c125_b125_w075_d095",
                ),
            }
        )
    return gates
