"""Create runtime-safe G5.21 split context/family/candidate feature tables."""

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

from repair5g521_common import (  # noqa: E402
    G521_CANDIDATE_FEATURES_CSV,
    G521_CANDIDATE_TARGETS_CSV,
    G521_CLOSED_CLAIMS,
    G521_CONTEXT_FEATURES_CSV,
    G521_CONTEXT_TARGETS_CSV,
    G521_FAMILY_FEATURES_CSV,
    G521_FAMILY_TARGETS_CSV,
    G521_FEATURES_REPORT,
    G521_FEATURES_SUMMARY,
    boolish,
    candidate_params,
    csv_number,
    feature_columns,
    finite_number,
    leakage_scan,
    numeric_candidate_param_dict,
    old14_candidate_ids,
    param_distance,
    read_rows,
    repo_root,
    write_json_file,
    write_rows,
    write_text_file,
)


PARAM_FIELDS = [
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
    parser.add_argument("--context-targets-csv", type=Path, default=Path(G521_CONTEXT_TARGETS_CSV))
    parser.add_argument("--family-targets-csv", type=Path, default=Path(G521_FAMILY_TARGETS_CSV))
    parser.add_argument("--candidate-targets-csv", type=Path, default=Path(G521_CANDIDATE_TARGETS_CSV))
    parser.add_argument("--context-output-csv", type=Path, default=Path(G521_CONTEXT_FEATURES_CSV))
    parser.add_argument("--family-output-csv", type=Path, default=Path(G521_FAMILY_FEATURES_CSV))
    parser.add_argument("--candidate-output-csv", type=Path, default=Path(G521_CANDIDATE_FEATURES_CSV))
    parser.add_argument("--report", type=Path, default=Path(G521_FEATURES_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_FEATURES_SUMMARY))
    return parser.parse_args(argv)


def context_features(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["feature_context_agents"] = finite_number(row.get("agents"), 0.0)
    out["feature_context_log_agents"] = math.log1p(max(0.0, finite_number(row.get("agents"), 0.0)))
    out["feature_context_iteration"] = finite_number(row.get("iteration"), 0.0)
    for name, value in row.items():
        if name.startswith("feature_map_") or name.startswith("feature_rich_"):
            out[name] = value
    return out


def add_family_features(rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates_by_context_family: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    families = sorted({str(row.get("candidate_family", "")) for row in rows})
    for row in candidate_rows:
        candidates_by_context_family[(str(row.get("normalized_context_key", "")), str(row.get("candidate_family", "")))].append(row)
    out = []
    for row in rows:
        actual = dict(row)
        family = str(row.get("candidate_family", ""))
        for item in families:
            actual[f"feature_family_id_{item}"] = 1.0 if item == family else 0.0
        members = candidates_by_context_family[(str(row.get("normalized_context_key", "")), family)]
        actual["feature_family_candidate_count"] = len(members)
        for field in PARAM_FIELDS:
            values = [finite_number(member.get(field), 0.0) for member in members if str(member.get(field, "")) != ""]
            actual[f"feature_family_mean_{field}"] = csv_number(sum(values) / len(values) if values else 0.0)
            actual[f"feature_family_span_{field}"] = csv_number((max(values) - min(values)) if values else 0.0)
        out.append(actual)
    return out


def nearest_old_features(candidate_id: str, old_ids: list[str]) -> dict[str, Any]:
    params = candidate_params(candidate_id)
    best = ("", math.inf)
    for old in old_ids:
        distance = param_distance(params, candidate_params(old))
        if distance < best[1] or (distance == best[1] and old < best[0]):
            best = (old, distance)
    return {
        "nearest_old_candidate": best[0],
        "nearest_old_param_distance": csv_number(best[1]),
        "feature_nearest_old_param_distance": csv_number(best[1]),
        "feature_nearest_old_param_distance_log": csv_number(math.log1p(max(0.0, best[1])) if math.isfinite(best[1]) else 0.0),
    }


def add_candidate_features(rows: list[dict[str, Any]], context_by_key: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    root = repo_root()
    old_ids = old14_candidate_ids(root)
    out = []
    roles = sorted({str(row.get("candidate_role", "")) for row in rows})
    families = sorted({str(row.get("candidate_family", "")) for row in rows})
    for row in rows:
        actual = dict(row)
        context = context_by_key.get(str(row.get("normalized_context_key", "")), {})
        for name, value in context.items():
            if name.startswith("feature_context_") or name.startswith("feature_map_") or name.startswith("feature_rich_"):
                actual[name] = value
        params = numeric_candidate_param_dict(str(row.get("candidate_id", "")))
        for field, value in params.items():
            actual[f"feature_candidate_{field}"] = csv_number(value)
        for role in roles:
            actual[f"feature_candidate_role_{role}"] = 1.0 if str(row.get("candidate_role", "")) == role else 0.0
        for family in families:
            actual[f"feature_candidate_family_{family}"] = 1.0 if str(row.get("candidate_family", "")) == family else 0.0
        rich_progress = finite_number(actual.get("feature_rich_progress_ratio"), 0.0)
        rich_blocked = finite_number(actual.get("feature_rich_blocked_per_committed"), 0.0)
        rich_wait = finite_number(actual.get("feature_rich_wait_per_committed"), 0.0)
        rich_cost_span = finite_number(actual.get("feature_rich_cost_span"), 0.0)
        actual["feature_interaction_rich_progress_ratio_x_alpha_flow_progress"] = csv_number(rich_progress * params["alpha_flow_progress"])
        actual["feature_interaction_rich_blocked_per_committed_x_alpha_cong_blocked"] = csv_number(rich_blocked * params["alpha_cong_blocked"])
        actual["feature_interaction_rich_wait_per_committed_x_alpha_flow_wait_or_nonprogress"] = csv_number(rich_wait * params["alpha_flow_wait_or_nonprogress"])
        actual["feature_interaction_rich_cost_span_x_flow_shield_beta"] = csv_number(rich_cost_span * params["flow_shield_beta"])
        actual.update(nearest_old_features(str(row.get("candidate_id", "")), old_ids))
        out.append(actual)
    add_centered(out, PARAM_FIELDS, group_fields=["normalized_context_key"], prefix="feature_centered_candidate_")
    add_centered(out, PARAM_FIELDS, group_fields=["normalized_context_key", "candidate_family"], prefix="feature_family_local_centered_candidate_")
    return out


def add_centered(rows: list[dict[str, Any]], fields: list[str], *, group_fields: list[str], prefix: str) -> None:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(field, "")) for field in group_fields)].append(row)
    for group in grouped.values():
        for field in fields:
            source = f"feature_candidate_{field}"
            values = [finite_number(row.get(source), 0.0) for row in group]
            mean_value = sum(values) / len(values) if values else 0.0
            for row in group:
                row[f"{prefix}{field}"] = csv_number(finite_number(row.get(source), 0.0) - mean_value)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    context_target_rows = read_rows(args.context_targets_csv)
    family_target_rows = read_rows(args.family_targets_csv)
    candidate_target_rows = read_rows(args.candidate_targets_csv)
    context_rows = [context_features(row) for row in context_target_rows]
    context_by_key = {str(row.get("normalized_context_key", "")): row for row in context_rows}
    candidate_rows = add_candidate_features(candidate_target_rows, context_by_key)
    family_rows = add_family_features(family_target_rows, candidate_target_rows)
    feature_names = sorted(set(feature_columns(context_rows) + feature_columns(family_rows) + feature_columns(candidate_rows)))
    leak = leakage_scan(feature_names)
    gates = {
        "context_rows_gt_0": len(context_rows) > 0,
        "family_rows_gt_0": len(family_rows) > 0,
        "candidate_rows_gt_0": len(candidate_rows) > 0,
        "context_feature_columns_present": any(name.startswith("feature_context_") for name in feature_columns(context_rows)),
        "family_feature_columns_present": any(name.startswith("feature_family_") for name in feature_columns(family_rows)),
        "candidate_feature_columns_present": any(name.startswith("feature_candidate_") for name in feature_columns(candidate_rows)),
        "nearest_old_features_present": any(name.startswith("feature_nearest_old_") for name in feature_columns(candidate_rows)),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = "split_features_v10_passed_continue_selector_eval" if all(gates.values()) else "split_features_v10_failed"
    summary = {
        "schema_version": "phase5p5_repair5g521_split_context_family_candidate_features_summary_v1",
        "decision": decision,
        "context_rows": len(context_rows),
        "family_rows": len(family_rows),
        "candidate_rows": len(candidate_rows),
        "context_feature_count": len(feature_columns(context_rows)),
        "family_feature_count": len(feature_columns(family_rows)),
        "candidate_feature_count": len(feature_columns(candidate_rows)),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **G521_CLOSED_CLAIMS,
    }
    write_rows(args.context_output_csv, context_rows)
    write_rows(args.family_output_csv, family_rows)
    write_rows(args.candidate_output_csv, candidate_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.21 Split Context/Family/Candidate Features\n\n"
        f"- decision: `{decision}`\n"
        f"- context_rows: `{len(context_rows)}`\n"
        f"- family_rows: `{len(family_rows)}`\n"
        f"- candidate_rows: `{len(candidate_rows)}`\n"
        f"- context_feature_count: `{summary['context_feature_count']}`\n"
        f"- family_feature_count: `{summary['family_feature_count']}`\n"
        f"- candidate_feature_count: `{summary['candidate_feature_count']}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "candidate_feature_count": summary["candidate_feature_count"], "forbidden_feature_count": leak["forbidden_feature_count"]}))
    return 0 if decision != "split_features_v10_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
