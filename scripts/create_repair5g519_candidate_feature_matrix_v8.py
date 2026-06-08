"""Build the G5.19 v8 candidate feature matrix over 22 full-primary candidates."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    G514_RICH_CONTEXT_FEATURES,
    G519_CLOSED_CLAIMS,
    G519_FEATURE_MATRIX_CSV,
    G519_FEATURE_MATRIX_REPORT,
    G519_FEATURE_MATRIX_SUMMARY,
    G519_TARGETS_CSV,
    boolish,
    compact_counter,
    csv_number,
    feature_columns,
    finite_number,
    forbidden_feature_scan,
    map_family,
    numeric_candidate_param_dict,
    observed_id_flags,
    perf_feature_columns,
    read_rows,
    rows_by_context,
    write_json_file,
    write_rows,
    write_text_file,
)


RICH_INTERACTIONS = [
    ("rich_blocked_per_committed", "alpha_cong_blocked", "feature_interaction_rich_blocked_per_committed_x_alpha_cong_blocked"),
    ("rich_blocked_per_agent", "alpha_cong_blocked", "feature_interaction_rich_blocked_per_agent_x_alpha_cong_blocked"),
    ("rich_wait_per_committed", "alpha_flow_wait_or_nonprogress", "feature_interaction_rich_wait_per_committed_x_alpha_flow_wait_or_nonprogress"),
    ("rich_wait_event_count", "alpha_flow_wait_or_nonprogress", "feature_interaction_rich_wait_event_count_x_alpha_flow_wait_or_nonprogress"),
    ("rich_progress_ratio", "alpha_flow_progress", "feature_interaction_rich_progress_ratio_x_alpha_flow_progress"),
    ("rich_committed_per_agent", "alpha_cong_committed", "feature_interaction_rich_committed_per_agent_x_alpha_cong_committed"),
    ("rich_c_flow_update_ratio", "flow_shield_beta", "feature_interaction_rich_c_flow_update_ratio_x_flow_shield_beta"),
    ("rich_c_flow_update_ratio", "max_flow_shield", "feature_interaction_rich_c_flow_update_ratio_x_max_flow_shield"),
    ("rich_c_update_count", "rho_cong", "feature_interaction_rich_c_update_count_x_rho_cong"),
    ("rich_f_update_count", "rho_flow", "feature_interaction_rich_f_update_count_x_rho_flow"),
    ("rich_cost_span", "flow_shield_beta", "feature_interaction_rich_cost_span_x_flow_shield_beta"),
    ("rich_cost_span", "max_flow_shield", "feature_interaction_rich_cost_span_x_max_flow_shield"),
    ("rich_cost_max", "max_flow_shield", "feature_interaction_rich_cost_max_x_max_flow_shield"),
]

RICH_BASE_FIELDS = [
    "rich_committed_count",
    "rich_blocked_count",
    "rich_wait_event_count",
    "rich_progress_committed_count",
    "rich_nonprogress_committed_count",
    "rich_blocked_per_committed",
    "rich_wait_per_committed",
    "rich_blocked_per_agent",
    "rich_committed_per_agent",
    "rich_progress_ratio",
    "rich_c_update_count",
    "rich_f_update_count",
    "rich_c_nonzero_edges",
    "rich_f_nonzero_edges",
    "rich_c_flow_update_ratio",
    "rich_cost_min",
    "rich_cost_max",
    "rich_cost_span",
]

CANDIDATE_PARAM_FIELDS = [
    "alpha_cong_committed",
    "alpha_cong_blocked",
    "alpha_flow_progress",
    "alpha_flow_wait_or_nonprogress",
    "rho_cong",
    "rho_flow",
    "flow_shield_beta",
    "max_flow_shield",
    "c_only",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G519_TARGETS_CSV))
    parser.add_argument("--rich-context-csv", type=Path, default=Path(G514_RICH_CONTEXT_FEATURES))
    parser.add_argument("--output-csv", type=Path, default=Path(G519_FEATURE_MATRIX_CSV))
    parser.add_argument("--report", type=Path, default=Path(G519_FEATURE_MATRIX_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_FEATURE_MATRIX_SUMMARY))
    return parser.parse_args(argv)


def centered_name(feature: str) -> str:
    return "feature_centered_" + feature[len("feature_") :]


def add_centered_features(rows: list[dict[str, Any]], features: list[str]) -> list[str]:
    out_names = [centered_name(feature) for feature in features]
    for feature, out_col in zip(features, out_names):
        for group in rows_by_context(rows).values():
            values = [finite_number(row.get(feature), 0.0) for row in group]
            mu = sum(values) / len(values) if values else 0.0
            for row in group:
                row[out_col] = csv_number(finite_number(row.get(feature), 0.0) - mu)
    return out_names


def family_one_hot_name(family: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in family.lower()).strip("_") or "unknown"
    return f"feature_candidate_family_{safe}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = [dict(row) for row in read_rows(args.targets_csv)]
    rich_by_context = {str(row.get("normalized_context_key", "")): row for row in read_rows(args.rich_context_csv)}
    families = sorted({str(row.get("candidate_family", "unknown")) for row in targets})
    map_families = ["empty", "maze", "random", "room", "warehouse", "other"]
    rows: list[dict[str, Any]] = []

    for row in targets:
        out = dict(row)
        rich = rich_by_context.get(str(row.get("normalized_context_key", "")), {})
        agents = finite_number(row.get("agents"), 0.0)
        trace_count = finite_number(rich.get("rich_committed_count"), 0.0) + finite_number(rich.get("rich_blocked_count"), 0.0) + finite_number(rich.get("rich_wait_event_count"), 0.0)
        fam = map_family(str(row.get("map", "")))
        out["feature_map_agents"] = csv_number(agents)
        out["feature_map_log_agents"] = csv_number(math.log1p(max(0.0, agents)))
        out["feature_map_iteration"] = csv_number(finite_number(row.get("iteration"), 0.0))
        out["feature_map_trace_event_count"] = csv_number(trace_count)
        out["feature_map_trace_events_per_agent"] = csv_number(trace_count / agents if agents > 0 else 0.0)
        out["feature_map_trace_events_log"] = csv_number(math.log1p(max(0.0, trace_count)))
        for name in map_families:
            out[f"feature_map_family_{name}"] = 1.0 if fam == name else 0.0

        for field in RICH_BASE_FIELDS:
            out[field] = rich.get(field, rich.get(f"feature_{field}", ""))
            out[f"feature_{field}"] = csv_number(finite_number(rich.get(f"feature_{field}", rich.get(field, 0.0)), 0.0))
        out["rich_feature_source"] = rich.get("feature_source", "")
        out["rich_source_checkpoint_path"] = rich.get("source_checkpoint_path", "")
        out["rich_context_feature_present"] = bool(rich)

        params = numeric_candidate_param_dict(str(row.get("candidate_id", "")))
        for field in CANDIDATE_PARAM_FIELDS:
            out[f"feature_candidate_{field}"] = csv_number(params[field])
        out["feature_candidate_is_old14_candidate"] = 1.0 if boolish(row.get("is_old14_candidate")) else 0.0
        out["feature_candidate_is_g518_new_candidate"] = 1.0 if boolish(row.get("is_new_candidate")) else 0.0
        out["feature_candidate_is_static_fallback"] = 1.0 if row.get("candidate_id") == "repair5g59_static_flow_shield" else 0.0
        out["feature_candidate_is_additive_fallback"] = 1.0 if row.get("candidate_id") == "repair5g59_additive_fallback" else 0.0
        for family in families:
            out[family_one_hot_name(family)] = 1.0 if row.get("candidate_family") == family else 0.0

        for rich_field, param_field, out_col in RICH_INTERACTIONS:
            out[out_col] = csv_number(
                finite_number(out.get(f"feature_{rich_field}", out.get(rich_field)), 0.0)
                * finite_number(out.get(f"feature_candidate_{param_field}"), 0.0)
            )
        rows.append(out)

    candidate_param_features = [f"feature_candidate_{field}" for field in CANDIDATE_PARAM_FIELDS]
    interaction_features = [item[2] for item in RICH_INTERACTIONS]
    centered_features = add_centered_features(rows, candidate_param_features + interaction_features)

    leak = forbidden_feature_scan(rows)
    flags = observed_id_flags(rows)
    candidate_counts = compact_counter(({"context": row.get("normalized_context_key", "")} for row in rows), "context")
    features = feature_columns(rows)
    perf_features = perf_feature_columns(rows)
    gates = {
        "rows_eq_1320": len(rows) == 1320,
        "contexts_eq_60": len(candidate_counts) == 60,
        "candidates_per_context_eq_22": all(count == 22 for count in candidate_counts.values()),
        "new_candidate_rows_eq_480": sum(1 for row in rows if boolish(row.get("is_new_candidate"))) == 480,
        "old_candidate_rows_eq_840": sum(1 for row in rows if boolish(row.get("is_old14_candidate"))) == 840,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "candidate_param_features_present": all(name in features for name in candidate_param_features),
        "rich_context_features_present": any(name.startswith("feature_rich_") for name in features),
        "rich_x_candidate_interactions_present": all(name in features for name in interaction_features),
        "within_context_centered_features_present": all(name in features for name in centered_features),
        "audit_only_surrogate_metadata_excluded_from_perf_model": "surrogate_selection_score" not in perf_features,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    decision = "feature_matrix_v8_passed_continue_ranker_suite" if all(gates.values()) else "feature_matrix_v8_failed"
    summary = {
        "schema_version": "phase5p5_repair5g519_candidate_feature_matrix_v8_summary_v1",
        "decision": decision,
        "rows": len(rows),
        "contexts": len(candidate_counts),
        "candidates_per_context_min": min(candidate_counts.values()) if candidate_counts else 0,
        "candidates_per_context_max": max(candidate_counts.values()) if candidate_counts else 0,
        "new_candidate_rows": sum(1 for row in rows if boolish(row.get("is_new_candidate"))),
        "old_candidate_rows": sum(1 for row in rows if boolish(row.get("is_old14_candidate"))),
        "feature_count": len(features),
        "perf_feature_count": len(perf_features),
        "candidate_param_feature_count": len(candidate_param_features),
        "rich_interaction_feature_count": len(interaction_features),
        "within_context_centered_feature_count": len(centered_features),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **flags,
        **G519_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Candidate Feature Matrix V8\n\n"
        f"- decision: `{decision}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- contexts: `{len(candidate_counts)}`\n"
        f"- feature_count: `{len(features)}`\n"
        f"- perf_feature_count: `{len(perf_features)}`\n"
        f"- new_candidate_rows: `{summary['new_candidate_rows']}`\n"
        f"- old_candidate_rows: `{summary['old_candidate_rows']}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- candidate_param_feature_count: `{len(candidate_param_features)}`\n"
        f"- rich_interaction_feature_count: `{len(interaction_features)}`\n"
        f"- within_context_centered_feature_count: `{len(centered_features)}`\n"
        "- audit_only_surrogate_metadata_excluded_from_perf_model: `true`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "V8 combines runtime-safe context features, bounded candidate parameters, rich context by candidate interactions, and within-context centered candidate-varying features. "
        "Surrogate selection metadata remains audit-only and is excluded from `feature_*` performance columns.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "feature_count": len(features)}))
    return 0 if decision != "feature_matrix_v8_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
