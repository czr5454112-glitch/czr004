"""Build the G5.20 opportunity-gated v9 feature matrix with runtime-safe features."""

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

from repair5g520_common import (  # noqa: E402
    G519_FEATURE_MATRIX_CSV,
    G520_CLOSED_CLAIMS,
    G520_FEATURE_MATRIX_CSV,
    G520_FEATURE_MATRIX_REPORT,
    G520_FEATURE_MATRIX_SUMMARY,
    G520_TARGETS_CSV,
    boolish,
    compact_counter,
    csv_number,
    feature_columns,
    finite_number,
    g520_perf_feature_columns,
    leakage_scan,
    read_rows,
    row_key,
    write_json_file,
    write_rows,
    write_text_file,
)


CANDIDATE_PARAM_FEATURES = [
    "feature_candidate_alpha_cong_committed",
    "feature_candidate_alpha_cong_blocked",
    "feature_candidate_alpha_flow_progress",
    "feature_candidate_alpha_flow_wait_or_nonprogress",
    "feature_candidate_rho_cong",
    "feature_candidate_rho_flow",
    "feature_candidate_flow_shield_beta",
    "feature_candidate_max_flow_shield",
    "feature_candidate_c_only",
]

FAMILY_LOCAL_BASE_FEATURES = [
    *CANDIDATE_PARAM_FEATURES,
    "feature_interaction_rich_progress_ratio_x_alpha_flow_progress",
    "feature_interaction_rich_c_flow_update_ratio_x_flow_shield_beta",
    "feature_interaction_rich_cost_max_x_max_flow_shield",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G520_TARGETS_CSV))
    parser.add_argument("--v8-feature-csv", type=Path, default=Path(G519_FEATURE_MATRIX_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G520_FEATURE_MATRIX_CSV))
    parser.add_argument("--report", type=Path, default=Path(G520_FEATURE_MATRIX_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G520_FEATURE_MATRIX_SUMMARY))
    return parser.parse_args(argv)


def centered_name(feature: str) -> str:
    return "feature_family_local_centered_" + feature[len("feature_") :]


def add_family_local_centered(rows: list[dict[str, Any]], features: list[str]) -> list[str]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("normalized_context_key", "")), str(row.get("candidate_family", "")))].append(row)
    out_names = [centered_name(feature) for feature in features]
    for group in grouped.values():
        for feature, out_name in zip(features, out_names):
            values = [finite_number(row.get(feature), 0.0) for row in group]
            mean_value = sum(values) / len(values) if values else 0.0
            for row in group:
                row[out_name] = csv_number(finite_number(row.get(feature), 0.0) - mean_value)
        for row in group:
            row["feature_family_local_candidate_count"] = len(group)
    return out_names + ["feature_family_local_candidate_count"]


def add_g520_features(row: dict[str, Any]) -> None:
    is_new = 1.0 if boolish(row.get("is_new_candidate")) else 0.0
    is_old = 1.0 if boolish(row.get("is_old14_candidate")) else 0.0
    row["feature_candidate_source_old14"] = is_old
    row["feature_candidate_source_g518_new"] = is_new
    row["feature_specialist_is_new_candidate"] = is_new
    for field in [
        "alpha_cong_blocked",
        "alpha_flow_progress",
        "alpha_flow_wait_or_nonprogress",
        "flow_shield_beta",
        "max_flow_shield",
    ]:
        source = f"feature_candidate_{field}"
        row[f"feature_specialist_new_x_{field}"] = csv_number(is_new * finite_number(row.get(source), 0.0))
    distance = finite_number(row.get("nearest_old_param_distance"), 0.0)
    row["feature_nearest_old_param_distance"] = csv_number(distance)
    row["feature_nearest_old_param_distance_log"] = csv_number(math.log1p(max(0.0, distance)))
    row["feature_nearest_old_same_family_hint"] = (
        1.0
        if str(row.get("candidate_family", "")) and str(row.get("candidate_family", "")) in str(row.get("nearest_old_candidate", ""))
        else 0.0
    )
    row["feature_nearest_old_distance_x_rich_progress_ratio"] = csv_number(
        distance * finite_number(row.get("feature_rich_progress_ratio"), 0.0)
    )
    row["feature_nearest_old_distance_x_rich_cost_span"] = csv_number(
        distance * finite_number(row.get("feature_rich_cost_span"), 0.0)
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = read_rows(args.targets_csv)
    v8_by_key = {row_key(row): row for row in read_rows(args.v8_feature_csv)}
    rows: list[dict[str, Any]] = []
    for target in targets:
        source = v8_by_key.get(row_key(target), {})
        out = dict(target)
        for name, value in source.items():
            if name.startswith("feature_") or name.startswith("rich_"):
                out[name] = value
        out["rich_context_feature_present"] = source.get("rich_context_feature_present", "")
        add_g520_features(out)
        rows.append(out)

    centered_features = add_family_local_centered(rows, FAMILY_LOCAL_BASE_FEATURES)
    features = feature_columns(rows)
    perf_features = g520_perf_feature_columns(rows)
    leak = leakage_scan(perf_features)
    context_counts = compact_counter(rows, "normalized_context_key")
    gates = {
        "rows_eq_1320": len(rows) == 1320,
        "contexts_eq_60": len(context_counts) == 60,
        "candidates_per_context_eq_22": all(count == 22 for count in context_counts.values()),
        "runtime_safe_feature_count_gt_v8": len(perf_features) > 88,
        "new_specialist_features_present": any(name.startswith("feature_specialist_") for name in perf_features),
        "nearest_old_features_present": any(name.startswith("feature_nearest_old_") for name in perf_features),
        "family_local_centered_features_present": all(name in perf_features for name in centered_features),
        "opportunity_labels_not_features": not any("opportunity" in name.lower() for name in perf_features),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = "opportunity_feature_matrix_v9_passed_continue_policy_eval" if all(gates.values()) else "opportunity_feature_matrix_v9_failed"
    summary = {
        "schema_version": "phase5p5_repair5g520_opportunity_feature_matrix_v9_summary_v1",
        "decision": decision,
        "rows": len(rows),
        "contexts": len(context_counts),
        "candidate_rows_per_context_min": min(context_counts.values()) if context_counts else 0,
        "candidate_rows_per_context_max": max(context_counts.values()) if context_counts else 0,
        "feature_count": len(features),
        "perf_feature_count": len(perf_features),
        "new_specialist_feature_count": sum(1 for name in perf_features if name.startswith("feature_specialist_")),
        "nearest_old_feature_count": sum(1 for name in perf_features if name.startswith("feature_nearest_old_")),
        "family_local_centered_feature_count": len(centered_features),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **G520_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 Opportunity Feature Matrix V9\n\n"
        f"- decision: `{decision}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- contexts: `{len(context_counts)}`\n"
        f"- feature_count: `{len(features)}`\n"
        f"- perf_feature_count: `{len(perf_features)}`\n"
        f"- new_specialist_feature_count: `{summary['new_specialist_feature_count']}`\n"
        f"- nearest_old_feature_count: `{summary['nearest_old_feature_count']}`\n"
        f"- family_local_centered_feature_count: `{summary['family_local_centered_feature_count']}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "V9 keeps opportunity/oracle/corrected target labels as non-feature columns. Runtime-safe feature columns cover context, rich trace, candidate parameters, "
        "candidate source/family, rich-by-candidate interactions, within-context centered features inherited from v8, new-candidate specialist features, nearest-old distance features, and family-local centered features.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "perf_feature_count": len(perf_features), "forbidden_feature_count": leak["forbidden_feature_count"]}))
    return 0 if decision != "opportunity_feature_matrix_v9_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
