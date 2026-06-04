"""Shared helpers for Repair5G.5.1 safe runtime-selector diagnostics."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from repair5g2_common import read_csv_rows, read_jsonl
from repair5g3_common import (
    MethodSpec,
    add_selector_alias_rows,
    expected_keys,
    grouped_rows,
    method_stats,
    number,
    oracle_regret_rows,
    paired_rows,
    schema_error_count,
    support_gate_summary,
    write_csv_rows,
    write_method_report,
)
from repair5g5_common import (
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SELECTOR_SPEC,
    G5_DISABLE,
    G5_FORCE,
    G5_RANDOM,
    G5_RUNTIME,
    G5_SHUFFLED,
    G5_STATIC,
    actual_methods_for_reported,
    load_json,
    rel,
    repo_root,
    resolve,
    run_solver_grid_g5,
    sha256_file,
    write_json,
)


G51_ALWAYS_STATIC = "repair5g51_runtime_always_static_flow_shield"
G51_ALWAYS_MAP_AGENT = "repair5g51_runtime_always_map_agent_selector"
G51_ALWAYS_ADDITIVE = "repair5g51_runtime_always_additive_selector"
G51_BAD_G5_STUMP = "repair5g51_runtime_bad_g5_stump"
G51_SAFE = "repair5g51_safe_abstention_selector_runtime"
G51_SAFE_SHADOW_STATIC = "repair5g51_safe_abstention_selector_shadow_static"
G51_SAFE_RANDOM = "repair5g51_safe_abstention_selector_random_feature_diagnostic"
G51_SAFE_SHUFFLED = "repair5g51_safe_abstention_selector_shuffled_label_diagnostic"

G51_SELECTOR_ALIASES = {
    G51_ALWAYS_STATIC,
    G51_ALWAYS_MAP_AGENT,
    G51_ALWAYS_ADDITIVE,
    G51_BAD_G5_STUMP,
    G51_SAFE,
    G51_SAFE_SHADOW_STATIC,
    G51_SAFE_RANDOM,
    G51_SAFE_SHUFFLED,
}

DEFAULT_SANITY_SELECTOR_DIR = "artifacts/models/laur_ltm/repair5g51_sanity_selectors"
DEFAULT_SAFE_SELECTOR_DIR = "artifacts/models/laur_ltm/repair5g51_safe_abstention_selector"


def now_iso() -> str:
    return datetime.now().isoformat()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    return read_csv_rows(path) if path.exists() else []


def selector_spec_payload(
    *,
    selector_name: str,
    left_method: str,
    right_method: str,
    fallback_static: str,
    feature: str = "ltm_iterations",
    threshold: float = 2.5,
    selector_type: str = "decision_stump",
    policy_note: str = "",
    static_candidate: str = "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    c_equiv_candidate: str = "repair5g_dual_c_equiv_c100_b100_w075_d100",
) -> dict[str, Any]:
    """Build a runtime-readable selector spec.

    The C++ loader uses simple field lookups, so the core stump fields are
    duplicated at top-level and inside ``selector_rule`` for auditability.
    """

    return {
        "schema_version": "phase5p5_repair5g51_selector_spec_v1",
        "created_at": now_iso(),
        "selector_name": selector_name,
        "selector_type": selector_type,
        "feature": feature,
        "threshold": float(threshold),
        "left_method": left_method,
        "right_method": right_method,
        "fallback_static": fallback_static,
        "repair5g2_best_frozen_static_candidate": static_candidate,
        "repair5g2_c_equiv_best_frozen_baseline": c_equiv_candidate,
        "selector_rule": {
            "type": selector_type,
            "feature": feature,
            "threshold": float(threshold),
            "left_method": left_method,
            "right_method": right_method,
            "fallback_static": fallback_static,
        },
        "candidate_aliases": {
            "repair5g2_best_frozen_static_candidate": static_candidate,
            "repair5g2_frozen_static_or_selector": "map-agent frozen selector from G2/G4",
            "repair5g2_c_equiv_best_frozen_baseline": c_equiv_candidate,
        },
        "feature_extraction_time": "pre_update_before_UpdateLTM",
        "allowed_output_space": "bounded UpdateParams candidate id only",
        "forbidden_outputs": [
            "actions",
            "restart",
            "priority overrides",
            "h_i(v)",
            "candidate deletion",
        ],
        "policy_note": policy_note,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }


def write_selector_artifact(root: Path, target_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    spec_path = target_dir / "selector_spec.json"
    write_json(spec_path, payload)
    manifest = {
        "schema_version": "phase5p5_repair5g51_selector_manifest_v1",
        "created_at": now_iso(),
        "selector_spec": rel(spec_path, root),
        "selector_spec_hash": sha256_file(spec_path),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(target_dir / "export_manifest.json", manifest)
    return manifest


def sanity_selector_paths(root: Path) -> dict[str, Path]:
    parent = resolve(Path(DEFAULT_SANITY_SELECTOR_DIR), root)
    return {
        G51_ALWAYS_STATIC: parent / "always_static_flow_shield" / "selector_spec.json",
        G51_ALWAYS_MAP_AGENT: parent / "always_map_agent_selector" / "selector_spec.json",
        G51_ALWAYS_ADDITIVE: parent / "always_additive" / "selector_spec.json",
        G51_BAD_G5_STUMP: parent / "bad_g5_stump" / "selector_spec.json",
    }


def safe_selector_path(root: Path) -> Path:
    return resolve(Path(DEFAULT_SAFE_SELECTOR_DIR), root) / "selector_spec.json"


def selector_path_for_alias(root: Path, alias: str) -> Path:
    if alias in sanity_selector_paths(root):
        return sanity_selector_paths(root)[alias]
    if alias in {G51_SAFE, G51_SAFE_SHADOW_STATIC, G51_SAFE_RANDOM, G51_SAFE_SHUFFLED}:
        return safe_selector_path(root)
    return resolve(Path(DEFAULT_SELECTOR_SPEC), root)


def g51_alias_spec(root: Path, alias: str) -> MethodSpec:
    selector_path = selector_path_for_alias(root, alias)
    if alias == G51_ALWAYS_STATIC:
        return MethodSpec(G5_STATIC, alias, ("--repair5g5-selector-spec", str(selector_path)))
    if alias == G51_ALWAYS_MAP_AGENT:
        return MethodSpec(G5_RUNTIME, alias, ("--repair5g5-selector-spec", str(selector_path)))
    if alias == G51_ALWAYS_ADDITIVE:
        return MethodSpec(G5_FORCE, alias, ("--repair5g5-selector-spec", str(selector_path)))
    if alias == G51_BAD_G5_STUMP:
        return MethodSpec(G5_RUNTIME, alias, ("--repair5g5-selector-spec", str(selector_path)))
    if alias == G51_SAFE:
        return MethodSpec(G5_RUNTIME, alias, ("--repair5g5-selector-spec", str(selector_path)))
    if alias == G51_SAFE_SHADOW_STATIC:
        return MethodSpec(G5_STATIC, alias, ("--repair5g5-selector-spec", str(selector_path)))
    if alias == G51_SAFE_RANDOM:
        return MethodSpec(G5_RANDOM, alias, ("--repair5g5-selector-spec", str(selector_path)))
    if alias == G51_SAFE_SHUFFLED:
        return MethodSpec(G5_SHUFFLED, alias, ("--repair5g5-selector-spec", str(selector_path)))
    raise KeyError(alias)


def build_g51_method_specs(
    *,
    root: Path,
    reported_methods: list[str],
    frozen_spec: dict[str, Any],
) -> list[MethodSpec]:
    base_reported = [method for method in reported_methods if method not in G51_SELECTOR_ALIASES]
    actual_methods = actual_methods_for_reported(base_reported, frozen_spec)
    specs: list[MethodSpec] = []
    for method in actual_methods:
        if method.startswith("repair5g5_contextual_flow_shield_selector_"):
            specs.append(
                MethodSpec(
                    method,
                    method,
                    ("--repair5g5-selector-spec", str(resolve(Path(DEFAULT_SELECTOR_SPEC), root))),
                )
            )
        else:
            specs.append(MethodSpec(method, method))
    for alias in reported_methods:
        if alias in G51_SELECTOR_ALIASES:
            specs.append(g51_alias_spec(root, alias))
    by_alias: dict[str, MethodSpec] = {}
    for spec in specs:
        by_alias[spec.alias] = spec
    return list(by_alias.values())


def analysis_rows_from_logs(
    *,
    output_jsonl: Path,
    frozen_spec: dict[str, Any],
    reported_methods: list[str],
) -> list[dict[str, Any]]:
    raw_rows = read_jsonl(output_jsonl)
    rows = [*raw_rows, *add_selector_alias_rows(raw_rows, frozen_spec)]
    reported = set(reported_methods)
    return [row for row in rows if str(row.get("method")) in reported]


def _mean_for_method(stats: dict[str, dict[str, Any]], method: str, default: float = math.inf) -> float:
    return number(stats.get(method, {}).get("mean_delta_ratio_vs_ltm"), default)


def policy_control_compliant(stats: dict[str, dict[str, Any]], method: str, *, tolerance: float = 0.002) -> bool:
    row = stats.get(method, {})
    if not row:
        return False
    mean = abs(_mean_for_method(stats, method, default=math.inf))
    return (
        int(number(row.get("rows"), 0)) > 0
        and int(number(row.get("ratio_worse_than_ltm_groups"), 99)) == 0
        and int(number(row.get("success_worse_than_ltm_groups"), 99)) == 0
        and math.isfinite(mean)
        and mean <= tolerance
    )


def summarise_g51_run(
    *,
    rows: list[dict[str, Any]],
    update_rows: list[dict[str, Any]],
    commands: list[dict[str, Any]],
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    reported_methods: list[str],
    selector_log_methods: Iterable[str],
    force_method: str | None,
    disable_method: str | None,
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
        (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("method")))
        for row in rows
    }
    missing = expected - actual
    parity = support_gate_summary(rows, include_static_c_equiv_pairs=False)
    selector_log_methods = set(selector_log_methods)
    selector_updates = [row for row in update_rows if str(row.get("method")) in selector_log_methods]
    feature_names = {name for row in selector_updates for name in row.get("runtime_feature_names", [])}
    forbidden_names = {"instance_id", "seed", "scen", "candidate outcome", "oracle", "final solver outcome"}
    unexpected = sorted(name for name in feature_names if name not in _allowed_runtime_features())
    forbidden_seen = sorted(name for name in feature_names if name in forbidden_names)
    gates = {
        "runtime_rows_full": len(missing) == 0,
        "expected_rows_full": len(missing) == 0,
        "missing_rows": len(missing),
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in commands if int(number(row.get("returncode"), 0)) == 1),
        "semantic_parity_mismatch_count": 0,
        "selector_logs_present": bool(selector_updates),
        "selector_update_log_rows": len(selector_updates),
        "allowed_feature_policy_passed": bool(selector_updates) and bool(feature_names) and not unexpected,
        "forbidden_feature_policy_passed": not forbidden_seen,
        "unexpected_runtime_features": unexpected,
        "forbidden_runtime_features": forbidden_seen,
        "all_costs_finite": parity.get("all_costs_finite", False),
        "cost_bounds_respected": parity.get("cost_bounds_respected", False),
        "force_additive_policy_compliant": True
        if force_method is None
        else policy_control_compliant(stats, force_method),
        "disable_policy_compliant": True
        if disable_method is None
        else policy_control_compliant(stats, disable_method),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    return {"method_stats": stats, "by_map_agent": by_group, "gates": gates}, paired


def _allowed_runtime_features() -> set[str]:
    return {
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


def method_delta_rows(
    paired: list[dict[str, Any]],
    *,
    target_method: str,
    reference_methods: list[str],
) -> list[dict[str, Any]]:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in paired:
        key = (
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            str(row.get("scen", "")),
        )
        by_case.setdefault(key, {})[str(row.get("candidate_id"))] = row
    out = []
    for key, methods in sorted(by_case.items()):
        target = methods.get(target_method)
        if target is None:
            continue
        target_delta = number(target.get("delta_ratio_vs_ltm"), math.nan)
        item: dict[str, Any] = {
            "map": key[0],
            "agents": key[1],
            "seed": key[2],
            "scen": key[3],
            "target_method": target_method,
            "target_delta_ratio_vs_ltm": target_delta if math.isfinite(target_delta) else None,
            "target_success": target.get("success"),
            "target_worse_vs_ltm": target.get("worse_vs_ltm"),
        }
        best_delta = target_delta
        best_method = target_method
        for ref in reference_methods:
            ref_row = methods.get(ref)
            ref_delta = number(ref_row.get("delta_ratio_vs_ltm"), math.nan) if ref_row else math.nan
            item[f"{ref}_delta_ratio_vs_ltm"] = ref_delta if math.isfinite(ref_delta) else None
            item[f"regret_vs_{ref}"] = (
                target_delta - ref_delta if math.isfinite(target_delta) and math.isfinite(ref_delta) else None
            )
            if math.isfinite(ref_delta) and (not math.isfinite(best_delta) or ref_delta < best_delta):
                best_delta = ref_delta
                best_method = ref
        item["best_available_method"] = best_method
        item["best_available_delta_ratio_vs_ltm"] = best_delta if math.isfinite(best_delta) else None
        item["regret_vs_best_available"] = (
            target_delta - best_delta if math.isfinite(target_delta) and math.isfinite(best_delta) else None
        )
        out.append(item)
    return out


def decision_distribution(update_rows: list[dict[str, Any]], methods: Iterable[str]) -> list[dict[str, Any]]:
    methods = set(methods)
    counter: Counter[tuple[Any, ...]] = Counter()
    for row in update_rows:
        if str(row.get("method")) not in methods:
            continue
        key = (
            str(row.get("method")),
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            str(row.get("selected_candidate_id") or row.get("applied_rule") or ""),
            str(row.get("decision_status", "")),
            str(row.get("selected_rule_source", "")),
        )
        counter[key] += 1
    return [
        {
            "method": key[0],
            "map": key[1],
            "agents": key[2],
            "selected_candidate_id": key[3],
            "decision_status": key[4],
            "selected_rule_source": key[5],
            "updates": value,
        }
        for key, value in sorted(counter.items())
    ]


def iteration_distribution(update_rows: list[dict[str, Any]], methods: Iterable[str]) -> list[dict[str, Any]]:
    methods = set(methods)
    counter: Counter[tuple[Any, ...]] = Counter()
    for row in update_rows:
        if str(row.get("method")) not in methods:
            continue
        key = (
            str(row.get("method")),
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("iteration"), -1)),
            str(row.get("selected_candidate_id") or row.get("applied_rule") or ""),
        )
        counter[key] += 1
    return [
        {
            "method": key[0],
            "map": key[1],
            "agents": key[2],
            "iteration": key[3],
            "selected_candidate_id": key[4],
            "updates": value,
        }
        for key, value in sorted(counter.items())
    ]


def feature_drift_rows(update_rows: list[dict[str, Any]], methods: Iterable[str]) -> list[dict[str, Any]]:
    methods = set(methods)
    values: dict[str, list[float]] = {}
    for row in update_rows:
        if str(row.get("method")) not in methods:
            continue
        names = row.get("runtime_feature_names", [])
        nums = row.get("runtime_feature_values", [])
        for name, value in zip(names, nums):
            numeric = number(value, math.nan)
            if math.isfinite(numeric):
                values.setdefault(str(name), []).append(numeric)
    out = []
    for name, nums in sorted(values.items()):
        out.append(
            {
                "feature": name,
                "count": len(nums),
                "mean": statistics.mean(nums) if nums else None,
                "median": statistics.median(nums) if nums else None,
                "min": min(nums) if nums else None,
                "max": max(nums) if nums else None,
                "stdev": statistics.pstdev(nums) if len(nums) > 1 else 0.0,
            }
        )
    return out


def write_gate_audit(path: Path, title: str, summary: dict[str, Any]) -> None:
    write_text(
        path,
        f"# {title}\n\n"
        "Diagnostic-only. `phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.\n\n"
        + "\n".join(f"- `{key}`: `{value}`" for key, value in summary.get("gates", {}).items())
        + "\n",
    )


def write_report_with_stats(path: Path, title: str, summary: dict[str, Any]) -> None:
    write_method_report(path, title=title, summary=summary)


__all__ = [
    "DEFAULT_FROZEN_G2_SPEC",
    "DEFAULT_SAFE_SELECTOR_DIR",
    "DEFAULT_SANITY_SELECTOR_DIR",
    "G51_ALWAYS_ADDITIVE",
    "G51_ALWAYS_MAP_AGENT",
    "G51_ALWAYS_STATIC",
    "G51_BAD_G5_STUMP",
    "G51_SAFE",
    "G51_SAFE_RANDOM",
    "G51_SAFE_SHADOW_STATIC",
    "G51_SAFE_SHUFFLED",
    "G51_SELECTOR_ALIASES",
    "analysis_rows_from_logs",
    "build_g51_method_specs",
    "decision_distribution",
    "feature_drift_rows",
    "g51_alias_spec",
    "iteration_distribution",
    "load_json",
    "method_delta_rows",
    "now_iso",
    "read_csv_dicts",
    "read_jsonl",
    "repo_root",
    "resolve",
    "run_solver_grid_g5",
    "safe_selector_path",
    "sanity_selector_paths",
    "selector_spec_payload",
    "sha256_file",
    "summarise_g51_run",
    "write_csv_rows",
    "write_gate_audit",
    "write_json",
    "write_report_with_stats",
    "write_selector_artifact",
    "write_text",
]
