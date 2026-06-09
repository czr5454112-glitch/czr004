"""Shared helpers for Repair5G.3 diagnostic validation scripts."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import (  # noqa: E402
    BASELINE_METHOD,
    MethodSpec,
    SelectorDecision,
    audit_and_prepare_scenarios,
    boolish,
    bootstrap_summary,
    case_dict,
    dirty_state,
    expected_keys,
    finite,
    git_value,
    make_f4_best_runtime,
    map_defaults,
    method_specs_from_subset,
    number,
    parity_mismatch_rows,
    read_csv_rows,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    row_score,
    run_solver_grid,
    schema_error_count,
    support_gate_summary,
    synthesize_selector_rows,
    write_csv_rows,
    write_jsonl,
    write_update_summary,
)


MAPS = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
AGENTS = [50, 100]

CONTROL_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
]

SCALAR_BASELINES = [
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g_dual_c_equiv_c100_b100_w075_d095",
    "repair5g_dual_c_equiv_c100_b100_w075_d100",
]

FROZEN_ALIASES = [
    "repair5g2_frozen_static_or_selector",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g2_g1_top_diagnostic_candidate",
]

FLOW_SHIELD_NEARBY = [
    "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
    "repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p5",
    "repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75",
    "repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75",
]

P4_SYNTHETIC_METHODS = [
    "repair5g3_random_flow_shield_diagnostic_seed0",
    "repair5g3_random_flow_shield_diagnostic_seed1",
    "repair5g3_random_flow_shield_diagnostic_seed2",
    "repair5g3_shuffled_flow_shield_diagnostic_seed0",
    "repair5g3_shuffled_flow_shield_diagnostic_seed1",
    "repair5g3_shuffled_goal_progress_diagnostic_seed0",
]

P3_SYNTHETIC_METHODS = [
    "repair5g2_shuffled_flow_shield_diagnostic",
    "repair5g2_random_candidate_diagnostic",
]


def now_iso() -> str:
    return datetime.now().isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def method_component(method: str) -> str:
    if method in CONTROL_METHODS:
        return "control"
    if method in FROZEN_ALIASES:
        if method == "repair5g2_frozen_static_or_selector":
            return "frozen_selector"
        if method == "repair5g2_best_frozen_static_candidate":
            return "frozen_static"
        if method == "repair5g2_c_equiv_best_frozen_baseline":
            return "c_equiv_baseline"
        return "flow_shield"
    if method.startswith("repair5g1_shield_"):
        return "flow_shield"
    if method.startswith("repair5g3_random") or method.startswith("repair5g3_shuffled"):
        return "synthetic"
    if method.startswith("repair5g2_random") or method.startswith("repair5g2_shuffled"):
        return "synthetic"
    if method.startswith("repair5g_dual_c_equiv_") or method in {
        "repair5f_static_c100_b100_w075_d090",
        "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
    }:
        return "c_equiv_baseline"
    return "diagnostic"


def subset_rows_for_methods(methods: Iterable[str]) -> list[dict[str, Any]]:
    rows = []
    for method in dict.fromkeys(methods):
        rows.append(
            {
                "runtime_method": method,
                "candidate_id": method,
                "component": method_component(method),
                "include_in_solver": not (
                    method in FROZEN_ALIASES
                    or method.startswith("repair5g3_random")
                    or method.startswith("repair5g3_shuffled")
                    or method.startswith("repair5g2_random")
                    or method.startswith("repair5g2_shuffled")
                ),
                "synthetic_diagnostic": method.startswith("repair5g3_")
                or method.startswith("repair5g2_random")
                or method.startswith("repair5g2_shuffled"),
                "diagnostic_only": True,
                "phase5p5_allowed": False,
                "phase6_allowed": False,
            }
        )
    return rows


def frozen_underlying_methods(spec: dict[str, Any]) -> list[str]:
    methods = []
    for key in [
        "selected_static_candidate",
        "selected_group_selector_default_candidate",
        "selected_c_equiv_baseline",
        "g1_top_diagnostic_candidate",
    ]:
        value = spec.get(key)
        if value:
            methods.append(str(value))
    for rule in spec.get("group_rules", []):
        if rule.get("candidate"):
            methods.append(str(rule["candidate"]))
    return list(dict.fromkeys(methods))


def decisions_from_frozen_spec(
    *,
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
) -> list[SelectorDecision]:
    cases = sorted(
        {
            (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)))
            for row in rows
        }
    )
    group_rules = {
        (str(rule.get("map")), int(rule.get("agents"))): str(rule.get("candidate"))
        for rule in spec.get("group_rules", [])
        if rule.get("candidate")
    }
    default_candidate = str(spec.get("selected_group_selector_default_candidate") or spec.get("selected_static_candidate"))
    out: list[SelectorDecision] = []
    for map_name, agents, seed in cases:
        selected = group_rules.get((map_name, agents), default_candidate)
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=selected,
                selector_alias="repair5g2_frozen_static_or_selector",
                selector_type=str(spec.get("selected_selector_type", "frozen_selector")),
                selected_source="frozen_group_rule" if (map_name, agents) in group_rules else "frozen_default",
            )
        )
        static = str(spec.get("selected_static_candidate", selected))
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=static,
                selector_alias="repair5g2_best_frozen_static_candidate",
                selector_type="best_frozen_static_candidate",
            )
        )
        c_equiv = str(spec.get("selected_c_equiv_baseline", "repair5g_dual_c_equiv_c100_b100_w075_d100"))
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=c_equiv,
                selector_alias="repair5g2_c_equiv_best_frozen_baseline",
                selector_type="c_equiv_frozen_baseline",
            )
        )
        g1_top = str(spec.get("g1_top_diagnostic_candidate", "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"))
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=g1_top,
                selector_alias="repair5g2_g1_top_diagnostic_candidate",
                selector_type="g1_top_diagnostic_comparator",
            )
        )
    return out


def g3_actual_methods(spec: dict[str, Any], *, broad: bool) -> list[str]:
    methods = [*CONTROL_METHODS]
    if broad:
        methods.extend(
            [
                "repair5f_static_c100_b100_w075_d090",
                "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
                "repair5g_dual_c_equiv_c100_b100_w075_d095",
                "repair5g_dual_c_equiv_c100_b100_w075_d100",
                *FLOW_SHIELD_NEARBY,
            ]
        )
    methods.extend(frozen_underlying_methods(spec))
    return list(dict.fromkeys(methods))


def build_specs(methods: Iterable[str], runtime_root: Path) -> list[MethodSpec]:
    return method_specs_from_subset(subset_rows_for_methods(methods), runtime_root)


def add_selector_alias_rows(rows: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = decisions_from_frozen_spec(spec=spec, rows=rows)
    return synthesize_selector_rows(rows, decisions)


def _group_rows_by_case(rows: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            str(row.get("scen", "")),
            row.get("repeat_index", ""),
            row.get("time_budget_sec", row.get("time_limit_sec", "")),
            row.get("ltm_iteration_budget", row.get("ltm_max_iterations", "")),
        )
        grouped.setdefault(key, {})[str(row.get("method"))] = row
    return grouped


def synthesize_seeded_diagnostics(
    rows: list[dict[str, Any]],
    *,
    synthetic_names: list[str],
    actual_candidate_methods: list[str],
) -> list[dict[str, Any]]:
    grouped = _group_rows_by_case(rows)
    ordered_cases = sorted(grouped)
    flow_methods = [method for method in actual_candidate_methods if method.startswith("repair5g1_shield_")]
    all_methods = [
        method
        for method in actual_candidate_methods
        if method not in CONTROL_METHODS and method != BASELINE_METHOD
    ]
    out: list[dict[str, Any]] = []
    for name in synthetic_names:
        seed = 0
        if "_seed" in name:
            try:
                seed = int(name.rsplit("_seed", 1)[1])
            except ValueError:
                seed = 0
        use_flow = "flow_shield" in name
        pool = flow_methods if use_flow else all_methods
        if not pool:
            continue
        for index, key in enumerate(ordered_cases):
            methods = grouped[key]
            source = ""
            if "random" in name:
                digest = hashlib.sha256(f"{key}|{name}|{seed}".encode("utf-8")).hexdigest()
                for offset in range(len(pool)):
                    candidate = pool[(int(digest[:12], 16) + offset) % len(pool)]
                    if candidate in methods:
                        source = candidate
                        break
            else:
                shifted = ordered_cases[(index + 1 + seed) % len(ordered_cases)]
                shifted_methods = grouped[shifted]
                present = [shifted_methods[item] for item in pool if item in shifted_methods]
                if present:
                    source = str(min(present, key=row_score).get("method"))
                if source not in methods:
                    present_here = [methods[item] for item in pool if item in methods]
                    if present_here:
                        source = str(min(present_here, key=row_score).get("method"))
            if source in methods:
                row = dict(methods[source])
                row["method"] = name
                row["repair5g3_synthetic_source_method"] = source
                out.append(row)
    return out


def paired_rows(rows: list[dict[str, Any]], *, dimensions: list[str] | None = None) -> list[dict[str, Any]]:
    dimensions = dimensions or []
    grouped = _group_rows_by_case(rows)
    out: list[dict[str, Any]] = []
    for key, methods in sorted(grouped.items()):
        base = methods.get(BASELINE_METHOD)
        if base is None:
            continue
        base_ratio = finite(base.get("sum_of_loss_ratio"))
        base_success = bool(base.get("success"))
        for method, row in sorted(methods.items()):
            if method == BASELINE_METHOD:
                continue
            ratio = finite(row.get("sum_of_loss_ratio"))
            delta = ratio - base_ratio if math.isfinite(ratio) and math.isfinite(base_ratio) else None
            item: dict[str, Any] = {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "scen": key[3],
                "candidate_id": method,
                "contender_method": method,
                "component": method_component(method),
                "baseline_method": BASELINE_METHOD,
                "baseline_success": base_success,
                "success": bool(row.get("success")),
                "baseline_ratio": base_ratio if math.isfinite(base_ratio) else None,
                "sum_of_loss_ratio": ratio if math.isfinite(ratio) else None,
                "delta_ratio_vs_ltm": delta,
                "better_vs_ltm": bool(row.get("success"))
                and ((not base_success) or (delta is not None and delta < -1.0e-12)),
                "equal_vs_ltm": delta is not None
                and abs(delta) <= 1.0e-12
                and bool(row.get("success")) == base_success,
                "worse_vs_ltm": base_success
                and ((not bool(row.get("success"))) or (delta is not None and delta > 1.0e-12)),
                "repair5g2_selected_source_method": row.get("repair5g2_selected_source_method", ""),
                "repair5g3_synthetic_source_method": row.get("repair5g3_synthetic_source_method", ""),
            }
            for dim in dimensions:
                item[dim] = row.get(dim, "")
            out.append(item)
    return out


def metrics_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [number(row.get("delta_ratio_vs_ltm")) for row in rows]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["map"]), int(number(row["agents"], 0))), []).append(row)
    return {
        "rows": len(rows),
        "better": sum(1 for row in rows if boolish(row.get("better_vs_ltm"))),
        "equal": sum(1 for row in rows if boolish(row.get("equal_vs_ltm"))),
        "worse": sum(1 for row in rows if boolish(row.get("worse_vs_ltm"))),
        "mean_delta_ratio_vs_ltm": statistics.mean([v for v in deltas if math.isfinite(v)])
        if any(math.isfinite(v) for v in deltas)
        else None,
        "median_delta_ratio_vs_ltm": statistics.median([v for v in deltas if math.isfinite(v)])
        if any(math.isfinite(v) for v in deltas)
        else None,
        "bootstrap": bootstrap_summary(deltas),
        "ratio_worse_than_ltm_groups": sum(
            1
            for group in grouped.values()
            if (statistics.mean([number(row.get("delta_ratio_vs_ltm")) for row in group]) if group else 0.0)
            > 1.0e-12
        ),
        "success_worse_than_ltm_groups": 0,
    }


def method_stats(long_rows: list[dict[str, Any]], *, method_field: str = "candidate_id") -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in long_rows:
        grouped.setdefault(str(row[method_field]), []).append(row)
    return {method: {**metrics_for_rows(group), "method": method} for method, group in sorted(grouped.items())}


def grouped_rows(
    long_rows: list[dict[str, Any]],
    *,
    group_fields: list[str],
    method_field: str = "candidate_id",
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in long_rows:
        key = tuple(row.get(field, "") for field in [*group_fields, method_field])
        grouped.setdefault(key, []).append(row)
    out = []
    for key, group in sorted(grouped.items()):
        item = {field: key[index] for index, field in enumerate([*group_fields, "method"])}
        item.update(metrics_for_rows(group))
        out.append(item)
    return out


def oracle_regret_rows(
    long_rows: list[dict[str, Any]],
    *,
    methods: list[str] | None = None,
    dimensions: list[str] | None = None,
) -> list[dict[str, Any]]:
    dimensions = dimensions or []
    by_case: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in long_rows:
        if methods is not None and str(row["candidate_id"]) not in methods:
            continue
        key = tuple(row.get(field, "") for field in ["map", "agents", "seed", "scen", *dimensions])
        by_case.setdefault(key, {})[str(row["candidate_id"])] = row
    out = []
    for key, rows_by_method in sorted(by_case.items()):
        if not rows_by_method:
            continue
        oracle_method, oracle_row = min(rows_by_method.items(), key=lambda item: number(item[1].get("delta_ratio_vs_ltm"), math.inf))
        base = {field: key[index] for index, field in enumerate(["map", "agents", "seed", "scen", *dimensions])}
        oracle_delta = number(oracle_row.get("delta_ratio_vs_ltm"), 0.0)
        for method, row in sorted(rows_by_method.items()):
            delta = number(row.get("delta_ratio_vs_ltm"), math.inf)
            out.append(
                {
                    **base,
                    "method": method,
                    "oracle_method": oracle_method,
                    "oracle_delta_ratio_vs_ltm": oracle_delta,
                    "method_delta_ratio_vs_ltm": delta if math.isfinite(delta) else None,
                    "regret_to_oracle": (delta - oracle_delta) if math.isfinite(delta) else None,
                }
            )
    return out


def write_method_report(path: Path, *, title: str, summary: dict[str, Any], stats_key: str = "method_stats") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary.get(stats_key, {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# {title}\n\n")
        handle.write("Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary.get("gates", {}).items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Scope\n\n")
        for key in ["maps", "agent_counts", "instance_ids", "time_limit_sec", "ltm_max_iterations", "row_count", "expected_row_count", "missing_rows", "schema_errors", "solver_crash_count"]:
            if key in summary:
                handle.write(f"- `{key}`: `{summary[key]}`\n")
        handle.write("\n## Method Stats\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for method, row in sorted(stats.items()):
            handle.write(
                f"| `{method}` | {row.get('rows')} | {row.get('better')} | {row.get('equal')} | "
                f"{row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
            )
        if summary.get("interpretation"):
            handle.write("\n## Interpretation\n\n")
            handle.write(str(summary["interpretation"]) + "\n")


def source_commit(path: Path, root: Path) -> str:
    try:
        return subprocess.check_output(["git", "log", "-1", "--format=%ct", "--", str(path)], cwd=root, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def artifact_manifest(paths: list[Path], *, root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        exists = path.exists()
        row: dict[str, Any] = {
            "path": rel(path, root),
            "exists": exists,
            "file_size_bytes": path.stat().st_size if exists else 0,
            "sha256": sha256_file(path) if exists and path.is_file() else "",
            "row_count": "",
            "parse_errors": 0,
            "duplicate_keys": 0,
            "missing_expected_keys": "",
        }
        if exists and path.suffix.lower() == ".jsonl":
            seen = set()
            duplicates = 0
            parse_errors = 0
            count = 0
            method_counts: Counter[str] = Counter()
            group_counts: Counter[str] = Counter()
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    count += 1
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        parse_errors += 1
                        continue
                    key = (
                        item.get("map"),
                        item.get("agents"),
                        item.get("seed"),
                        item.get("method"),
                    )
                    if key in seen:
                        duplicates += 1
                    seen.add(key)
                    method_counts[str(item.get("method", ""))] += 1
                    group_counts[f"{item.get('map','')}|{item.get('agents','')}"] += 1
            row.update(
                {
                    "row_count": count,
                    "parse_errors": parse_errors,
                    "duplicate_keys": duplicates,
                    "method_counts": json.dumps(dict(sorted(method_counts.items())), sort_keys=True),
                    "map_agent_counts": json.dumps(dict(sorted(group_counts.items())), sort_keys=True),
                }
            )
        elif exists and path.suffix.lower() == ".csv":
            csv_rows = read_csv_rows(path)
            row["row_count"] = len(csv_rows)
            if csv_rows:
                method_key = "method" if "method" in csv_rows[0] else "candidate_id" if "candidate_id" in csv_rows[0] else ""
                if method_key:
                    row["method_counts"] = json.dumps(dict(sorted(Counter(r.get(method_key, "") for r in csv_rows).items())), sort_keys=True)
        rows.append(row)
    return rows
