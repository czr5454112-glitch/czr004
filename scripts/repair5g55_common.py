"""Shared helpers for Repair5G.5.5 scaled counterfactual diagnostics."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from repair5g2_common import read_csv_rows
from repair5g3_common import number, read_jsonl, repo_root, resolve, write_csv_rows, write_json
from repair5g51_common import write_text
from repair5g54_common import (
    G54_ALLOWED_RUNTIME_FEATURES,
    G54_CANDIDATES,
    G54_FORBIDDEN_LABEL_FIELDS,
    boolish,
    load_json,
    parse_instance_id_tokens,
    score_from_label,
    validate_observed_instance_ids,
)


G55_MAPS = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
G55_AGENT_COUNTS = [50, 100]
G55_DEFAULT_INSTANCE_IDS = list(range(146, 166))
G55_SMOKE_INSTANCE_IDS = list(range(146, 156))
G55_BASE_CANDIDATES = list(G54_CANDIDATES)
G55_STATIC_CONTEXT_METHOD = "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"
G55_CONTEXT_ALIAS = "repair5g55_counterfactual_static_context"
G55_STATIC_CANDIDATE = "repair5g2_best_frozen_static_candidate"
G55_ADDITIVE_CANDIDATE = "additive_ltm"
G55_CONTEXT_MINIMUM_SMOKE = 60
G55_CONTEXT_TARGET = 120

G55_REQUIRED_FINAL_STATUS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "ids_166_205_untouched": True,
    "g6_training_allowed": False,
    "learned_runtime_fresh_holdout": "blocked_not_run",
}

G55_FORBIDDEN_FEATURE_NAMES = {
    *G54_FORBIDDEN_LABEL_FIELDS,
    "candidate_id",
    "resolved_candidate_id",
    "oracle_candidate_id",
    "oracle_score",
    "probe_sum_of_loss_ratio",
    "probe_sum_of_loss",
    "probe_solution_found",
    "probe_feasible",
    "final_full_run_outcome",
    "future_solution_outcome",
}


def parse_int_tokens(tokens: Iterable[Any]) -> list[int]:
    return parse_instance_id_tokens(tokens)


def validate_g55_instance_ids(tokens_or_ids: Iterable[Any], *, label: str = "Repair5G.5.5") -> list[int]:
    ids = parse_int_tokens(tokens_or_ids)
    return validate_observed_instance_ids(ids, label=label)


def compact_json_bool(value: Any) -> bool:
    return boolish(value)


def local_lattice_candidates() -> list[str]:
    """A deliberately small lattice around validated flow-shield rules."""

    scalar_rules = [
        "c100_b125_w075_d100",
        "c125_b125_w075_d095",
        "c125_b125_w075_d090",
    ]
    betas = ["0p2", "0p35", "0p5"]
    max_shields = ["0p5", "0p75"]
    return [
        f"repair5g1_shield_{rule}_beta{beta}_max{max_shield}"
        for rule in scalar_rules
        for beta in betas
        for max_shield in max_shields
    ]


def default_candidate_list(include_lattice: bool = False) -> list[str]:
    candidates = list(G55_BASE_CANDIDATES)
    if include_lattice:
        candidates.extend(local_lattice_candidates())
    return list(dict.fromkeys(candidates))


def candidate_list_from_csv(path: Path, *, default: list[str] | None = None) -> list[str]:
    if not path.exists():
        return list(default or G55_BASE_CANDIDATES)
    rows = read_csv_rows(path)
    out = [
        str(row.get("candidate_id", ""))
        for row in rows
        if str(row.get("candidate_id", "")) and boolish(row.get("include_in_default_scaled_labels", False))
    ]
    return list(dict.fromkeys(out or list(default or G55_BASE_CANDIDATES)))


def context_id_for(row: dict[str, Any], *, method: str | None = None) -> str:
    if row.get("context_id"):
        return str(row["context_id"])
    method = method or str(row.get("method") or G55_CONTEXT_ALIAS)
    return (
        f"{row.get('map', '')}|a{int(number(row.get('agents'), 0))}|"
        f"s{int(number(row.get('seed'), 0))}|it{int(number(row.get('iteration'), 0))}|{method}"
    )


def normalized_context_key(row: dict[str, Any]) -> tuple[str, int, int, int, str]:
    return (
        str(row.get("map", "")),
        int(number(row.get("agents"), 0)),
        int(number(row.get("seed"), 0)),
        int(number(row.get("iteration"), 0)),
        str(row.get("traffic_before_hash_full", "")),
    )


def group_by_context(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        context_id = context_id_for(row)
        if context_id:
            grouped[context_id].append(row)
    return dict(grouped)


def load_checkpoint_features(checkpoint_jsonl: Path) -> dict[str, dict[str, Any]]:
    checkpoints = read_jsonl(checkpoint_jsonl) if checkpoint_jsonl.exists() else []
    out: dict[str, dict[str, Any]] = {}
    for row in checkpoints:
        context_id = context_id_for(row)
        features = feature_values_from_checkpoint(row)
        out[context_id] = {
            **features,
            "checkpoint_trace_event_count": row.get("trace_event_count", ""),
            "checkpoint_replay_hash_match": row.get("replayed_traffic_after_hash_match", ""),
            "checkpoint_replay_stats_match": row.get("replayed_update_stats_match", ""),
            "checkpoint_forbidden_feature_audit_passed": row.get("forbidden_feature_audit_passed", True),
        }
    return out


def feature_values_from_checkpoint(row: dict[str, Any]) -> dict[str, Any]:
    names = [str(value) for value in row.get("feature_names", [])]
    values = row.get("feature_values", [])
    features = {name: values[index] for index, name in enumerate(names) if index < len(values)}
    if features:
        return features

    trace_events = row.get("trace_events", [])
    if not isinstance(trace_events, list):
        trace_events = []
    committed = [event for event in trace_events if str(event.get("kind")) == "committed"]
    blocked = [event for event in trace_events if str(event.get("kind")) == "blocked"]
    waits = [event for event in committed if event.get("from_id") == event.get("to_id")]
    progress = [event for event in committed if event.get("from_id") != event.get("to_id")]
    agents = number(row.get("agents"), 0.0)
    committed_count = len(committed)
    return {
        "agents": int(agents),
        "ltm_iterations": row.get("iteration", ""),
        "returned_solutions_count_so_far": row.get("returned_solutions_count_so_far", ""),
        "has_incumbent_before": row.get("has_incumbent_before", ""),
        "best_ratio_before": row.get("best_ratio_before", ""),
        "committed_count": committed_count,
        "blocked_count": len(blocked),
        "wait_event_count": len(waits),
        "progress_committed_count": len(progress),
        "nonprogress_committed_count": max(0, committed_count - len(progress)),
        "blocked_per_committed": len(blocked) / committed_count if committed_count else 0.0,
        "wait_per_committed": len(waits) / committed_count if committed_count else 0.0,
        "blocked_per_agent": len(blocked) / agents if agents else 0.0,
        "committed_per_agent": committed_count / agents if agents else 0.0,
        "progress_ratio": len(progress) / committed_count if committed_count else 0.0,
        "c_update_count": row.get("congestion_update_count", ""),
        "f_update_count": row.get("flow_update_count", ""),
        "cost_min": row.get("cost_audit_min_cost", ""),
        "cost_max": row.get("cost_audit_max_cost", ""),
        "cost_span": number(row.get("cost_audit_max_cost"), 0.0) - number(row.get("cost_audit_min_cost"), 0.0),
        "cost_bounds_respected": row.get("cost_audit_bounds_respected", ""),
    }


def finite_values(values: Iterable[Any]) -> list[float]:
    out: list[float] = []
    for value in values:
        numeric = number(value, math.nan)
        if math.isfinite(numeric):
            out.append(numeric)
    return out


def median_or_none(values: Iterable[Any]) -> float | None:
    finite = finite_values(values)
    return statistics.median(finite) if finite else None


def mean_or_none(values: Iterable[Any]) -> float | None:
    finite = finite_values(values)
    return sum(finite) / len(finite) if finite else None


def oracle_rows_from_labels(rows: list[dict[str, Any]], expected_candidates: Iterable[str]) -> list[dict[str, Any]]:
    required = set(expected_candidates)
    out: list[dict[str, Any]] = []
    for context_id, context_rows in sorted(group_by_context(rows).items()):
        seen = {str(row.get("candidate_id", "")) for row in context_rows}
        scored = [(score_from_label(row), row) for row in context_rows]
        finite = [(score, row) for score, row in scored if math.isfinite(score)]
        best_score, best_row = min(finite, key=lambda item: item[0]) if finite else (math.inf, {})
        static = next((row for row in context_rows if row.get("candidate_id") == G55_STATIC_CANDIDATE), {})
        additive = next((row for row in context_rows if row.get("candidate_id") == G55_ADDITIVE_CANDIDATE), {})
        static_score = score_from_label(static) if static else math.inf
        additive_score = score_from_label(additive) if additive else math.inf
        oracle_gap_static = best_score - static_score if math.isfinite(best_score) and math.isfinite(static_score) else math.nan
        oracle_gap_additive = best_score - additive_score if math.isfinite(best_score) and math.isfinite(additive_score) else math.nan
        first = context_rows[0]
        out.append(
            {
                "context_id": context_id,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "trace_event_count": first.get("trace_event_count", ""),
                "candidate_coverage_complete": required <= seen,
                "candidate_count": len(seen),
                "oracle_candidate_id": best_row.get("candidate_id", ""),
                "oracle_resolved_candidate_id": best_row.get("resolved_candidate_id", ""),
                "oracle_score": best_score if math.isfinite(best_score) else "",
                "static_score": static_score if math.isfinite(static_score) else "",
                "additive_score": additive_score if math.isfinite(additive_score) else "",
                "oracle_gap_over_static": oracle_gap_static if math.isfinite(oracle_gap_static) else "",
                "oracle_gap_over_additive": oracle_gap_additive if math.isfinite(oracle_gap_additive) else "",
                "oracle_beats_static": math.isfinite(oracle_gap_static) and oracle_gap_static < -1.0e-12,
                "oracle_beats_additive": math.isfinite(oracle_gap_additive) and oracle_gap_additive < -1.0e-12,
                "static_dominates_context": math.isfinite(oracle_gap_static) and oracle_gap_static >= -1.0e-12,
            }
        )
    return out


def context_rows_from_labels(
    labels: list[dict[str, Any]],
    oracle_rows: list[dict[str, Any]],
    checkpoint_features: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    checkpoint_features = checkpoint_features or {}
    oracle_by_context = {str(row.get("context_id", "")): row for row in oracle_rows}
    out: list[dict[str, Any]] = []
    for context_id, rows in sorted(group_by_context(labels).items()):
        first = rows[0]
        trace_count = number(first.get("trace_event_count"), 0.0)
        feature_row = checkpoint_features.get(context_id, {})
        blocked = number(feature_row.get("blocked_count"), math.nan)
        committed = number(feature_row.get("committed_count"), math.nan)
        wait = number(feature_row.get("wait_event_count"), math.nan)
        c_count = number(feature_row.get("c_update_count"), math.nan)
        f_count = number(feature_row.get("f_update_count"), math.nan)
        out.append(
            {
                "context_id": context_id,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "trace_event_count": trace_count,
                "candidate_rows": len(rows),
                "candidate_ids": ",".join(sorted({str(row.get("candidate_id", "")) for row in rows})),
                "oracle_candidate_id": oracle_by_context.get(context_id, {}).get("oracle_candidate_id", ""),
                "oracle_gap_over_static": oracle_by_context.get(context_id, {}).get("oracle_gap_over_static", ""),
                "oracle_gap_over_additive": oracle_by_context.get(context_id, {}).get("oracle_gap_over_additive", ""),
                "blocked_count": blocked if math.isfinite(blocked) else "",
                "committed_count": committed if math.isfinite(committed) else "",
                "wait_event_count": wait if math.isfinite(wait) else "",
                "blocked_per_committed": blocked / committed if math.isfinite(blocked) and committed > 0 else "",
                "wait_event_ratio": wait / committed if math.isfinite(wait) and committed > 0 else "",
                "c_update_count": c_count if math.isfinite(c_count) else "",
                "f_update_count": f_count if math.isfinite(f_count) else "",
                "c_flow_update_ratio": c_count / f_count if math.isfinite(c_count) and f_count > 0 else "",
                **{key: value for key, value in feature_row.items() if key in G54_ALLOWED_RUNTIME_FEATURES},
            }
        )
    return out


def write_gate_report(path: Path, title: str, gates: dict[str, Any], extra: str = "") -> None:
    lines = [f"# {title}", "", "Diagnostic-only. Phase5.5, Phase6, and AAAI-ready remain closed.", ""]
    lines.append("## Gates")
    lines.append("")
    lines.extend(f"- `{key}`: `{value}`" for key, value in gates.items())
    if extra:
        lines.extend(["", extra.rstrip()])
    write_text(path, "\n".join(lines) + "\n")


__all__ = [
    "G55_ADDITIVE_CANDIDATE",
    "G55_AGENT_COUNTS",
    "G55_BASE_CANDIDATES",
    "G55_CONTEXT_ALIAS",
    "G55_CONTEXT_MINIMUM_SMOKE",
    "G55_CONTEXT_TARGET",
    "G55_DEFAULT_INSTANCE_IDS",
    "G55_FORBIDDEN_FEATURE_NAMES",
    "G55_MAPS",
    "G55_REQUIRED_FINAL_STATUS",
    "G55_SMOKE_INSTANCE_IDS",
    "G55_STATIC_CANDIDATE",
    "G55_STATIC_CONTEXT_METHOD",
    "candidate_list_from_csv",
    "compact_json_bool",
    "context_id_for",
    "context_rows_from_labels",
    "default_candidate_list",
    "finite_values",
    "feature_values_from_checkpoint",
    "group_by_context",
    "load_checkpoint_features",
    "load_json",
    "local_lattice_candidates",
    "mean_or_none",
    "median_or_none",
    "normalized_context_key",
    "oracle_rows_from_labels",
    "parse_int_tokens",
    "read_csv_rows",
    "read_jsonl",
    "repo_root",
    "resolve",
    "validate_g55_instance_ids",
    "write_csv_rows",
    "write_gate_report",
    "write_json",
    "write_text",
]
