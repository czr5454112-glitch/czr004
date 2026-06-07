"""Create the G5.12 leakage-clean candidate feature matrix v3."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    CLOSED_CLAIMS,
    boolish,
    count_by,
    csv_number,
    finite_number,
    leakage_scan,
    map_family,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_candidate_feature_matrix_v3.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_candidate_feature_matrix_v3_summary.json"
MAP_FAMILIES = ["random", "maze", "warehouse", "empty", "room", "other"]
PARAMS = [
    "alpha_cong_committed",
    "alpha_cong_blocked",
    "alpha_flow_progress",
    "alpha_flow_wait_or_nonprogress",
    "rho_cong",
    "rho_flow",
    "flow_shield_beta",
    "max_flow_shield",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def feature_row(row: dict[str, object]) -> dict[str, object]:
    agents = finite_number(row.get("agents"), 0.0)
    trace_events = finite_number(row.get("trace_event_count"), 0.0)
    family = map_family(str(row.get("map", "")))
    out: dict[str, object] = {
        "context_id": row.get("context_id", ""),
        "normalized_context_key": row.get("normalized_context_key", ""),
        "map": row.get("map", ""),
        "agents": int(agents),
        "seed": int(finite_number(row.get("seed"), 0.0)),
        "iteration": int(finite_number(row.get("iteration"), 0.0)),
        "candidate_id": row.get("candidate_id", ""),
        "candidate_index": int(finite_number(row.get("candidate_index"), 0.0)),
        "split": row.get("split", ""),
        "label_class": row.get("label_class", ""),
        "target_weight": row.get("target_weight", ""),
        "mean_delta_vs_static_primary": row.get("mean_delta_vs_static_primary", ""),
        "mean_delta_vs_additive_primary": row.get("mean_delta_vs_additive_primary", ""),
        "oracle_regret_primary": row.get("oracle_regret_primary", ""),
        "rank_primary": row.get("rank_primary", ""),
        "helpful_vs_static": row.get("helpful_vs_static", ""),
        "harmful_vs_static": row.get("harmful_vs_static", ""),
        "near_static_neutral": row.get("near_static_neutral", ""),
        "oracle_candidate_for_context": row.get("oracle_candidate_for_context", ""),
        "score_1000": row.get("score_1000", ""),
        "score_2000": row.get("score_2000", ""),
        "static_score_1000": row.get("static_score_1000", ""),
        "static_score_2000": row.get("static_score_2000", ""),
        "additive_score_1000": row.get("additive_score_1000", ""),
        "additive_score_2000": row.get("additive_score_2000", ""),
        "observed_ids_only": row.get("observed_ids_only", ""),
        "ids_166_205_untouched": row.get("ids_166_205_untouched", ""),
        "feature_map_agents": csv_number(agents),
        "feature_map_log_agents": csv_number(math.log1p(agents)),
        "feature_map_iteration": csv_number(finite_number(row.get("iteration"), 0.0)),
        "feature_map_trace_event_count": csv_number(trace_events),
        "feature_map_trace_events_per_agent": csv_number(safe_ratio(trace_events, agents)),
        "feature_map_trace_events_log": csv_number(math.log1p(max(0.0, trace_events))),
    }
    for name in MAP_FAMILIES:
        out[f"feature_map_family_{name}"] = 1.0 if family == name else 0.0
    for name in PARAMS:
        out[f"feature_candidate_{name}"] = csv_number(finite_number(row.get(name), 0.0))
    out["feature_candidate_is_static_fallback"] = 1.0 if boolish(row.get("static_fallback")) else 0.0
    out["feature_candidate_is_additive_fallback"] = 1.0 if boolish(row.get("additive_fallback")) else 0.0
    out["feature_candidate_is_c_only_f_disabled"] = 1.0 if boolish(row.get("c_only_f_disabled")) else 0.0
    out["feature_candidate_is_goal_aware_dual_channel"] = 1.0 if not boolish(row.get("additive_fallback")) and not boolish(row.get("c_only_f_disabled")) else 0.0
    for name in PARAMS:
        value = finite_number(row.get(name), 0.0)
        out[f"feature_interaction_trace_events_x_{name}"] = csv_number(trace_events * value)
        out[f"feature_interaction_agents_x_{name}"] = csv_number(agents * value)
    out["feature_interaction_trace_per_agent_x_flow_shield_beta"] = csv_number(
        safe_ratio(trace_events, agents) * finite_number(row.get("flow_shield_beta"), 0.0)
    )
    out["feature_interaction_trace_per_agent_x_max_flow_shield"] = csv_number(
        safe_ratio(trace_events, agents) * finite_number(row.get("max_flow_shield"), 0.0)
    )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    target_rows = read_csv_rows(resolve(args.targets_csv, root))
    rows = [feature_row(row) for row in target_rows]
    feature_names = [name for name in rows[0] if name.startswith("feature_")] if rows else []
    leak = leakage_scan(feature_names)
    contexts = {str(row.get("normalized_context_key", "")) for row in rows}
    candidates = {str(row.get("candidate_id", "")) for row in rows}
    candidate_param_features = [name for name in feature_names if name.startswith("feature_candidate_")]
    interaction_features = [name for name in feature_names if name.startswith("feature_interaction_")]
    gates = {
        "perf_safe_candidate_rows_ge_840": len(rows) >= 840,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "candidate_param_features_present": len(candidate_param_features) > 0,
        "interaction_features_present": len(interaction_features) > 0,
        "train_dev_split_seed_based": count_by(rows, "split").get("train", 0) > 0 and count_by(rows, "split").get("dev", 0) > 0,
        "grouped_context_ids_preserved": len(contexts) == 60,
    }
    decision = "feature_v3_passed_continue_candidate_ranker" if all(gates.values()) else "feature_v3_failed_continue_feature_design"
    write_csv_rows(resolve(args.output_csv, root), rows)
    summary = {
        "schema_version": "phase5p5_repair5g512_candidate_feature_matrix_v3_summary_v1",
        "decision": decision,
        "perf_safe_candidate_rows": len(rows),
        "contexts": len(contexts),
        "candidates": len(candidates),
        "split_counts": count_by(rows, "split"),
        "feature_count": len(feature_names),
        "candidate_param_feature_count": len(candidate_param_features),
        "interaction_feature_count": len(interaction_features),
        "feature_names": feature_names,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "candidate_param_features_present": len(candidate_param_features) > 0,
        "interaction_features_present": len(interaction_features) > 0,
        "feature_signal_limited": True,
        "missing_runtime_context_features_reported": True,
        "feature_signal_limited_reason": "Tracked G5.11 artifacts expose map/agent/iteration/trace_event_count, but not rich pre-choice wait/block/progress trace aggregates.",
        "gates": gates,
        "feature_matrix_csv": str(resolve(args.output_csv, root)),
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Candidate Feature Matrix v3\n\n"
        f"- decision: `{decision}`\n"
        f"- perf_safe_candidate_rows: `{len(rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidates: `{len(candidates)}`\n"
        f"- split_counts: `{count_by(rows, 'split')}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- candidate_param_features_present: `{len(candidate_param_features) > 0}`\n"
        f"- interaction_features_present: `{len(interaction_features) > 0}`\n"
        f"- feature_signal_limited: `true`\n"
        f"- missing_runtime_context_features_reported: `true`\n"
        f"- gates: `{gates}`\n\n"
        "Performance-safe features are restricted to map/agent/iteration metadata, trace-event count, candidate parameters, "
        "candidate family flags, and interactions between available context counts and candidate parameters. "
        "Score, delta, oracle, regret, rank, label, target, probe, solution, action, priority, restart, h-value, and candidate-deletion fields are excluded from `feature_*` columns.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "forbidden_feature_count": leak["forbidden_feature_count"]}))
    return 0 if decision != "feature_v3_failed_continue_feature_design" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
