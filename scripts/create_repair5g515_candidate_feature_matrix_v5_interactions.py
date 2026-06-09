"""Create G5.15 v5 candidate matrix with rich-by-candidate interactions."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    csv_number,
    finite_number,
    leakage_scan,
    observed_id_flags,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g513_common import grouped_contexts  # noqa: E402
from repair5g515_common import (  # noqa: E402
    DEFAULT_V4_MATRIX,
    DEFAULT_V5_MATRIX,
    DEFAULT_V5_SUMMARY,
    G515_CLOSED_CLAIMS,
    REQUIRED_RICH_INTERACTIONS,
    context_only_rich_features,
    count_candidate_varying,
    feature_columns,
    interaction_feature_names,
    rank_feature_names,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_candidate_feature_matrix_v5.md"
LOG1P_FIELDS = [
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "progress_committed_count",
    "nonprogress_committed_count",
    "c_update_count",
    "f_update_count",
    "c_nonzero_edges",
    "f_nonzero_edges",
]
CAP_FIELDS = {
    "blocked_per_committed": 10.0,
    "wait_per_committed": 10.0,
    "blocked_per_agent": 200.0,
    "committed_per_agent": 500.0,
    "progress_ratio": 1.0,
    "c_flow_update_ratio": 10.0,
    "cost_span": 100.0,
    "cost_max": 100.0,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v4-csv", type=Path, default=Path(DEFAULT_V4_MATRIX))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_V5_MATRIX))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_V5_SUMMARY))
    return parser.parse_args(argv)


def train_z_name(feature: str) -> str:
    if feature.startswith("feature_rich_"):
        return "feature_rich_train_z_" + feature[len("feature_rich_") :]
    if feature.startswith("feature_interaction_"):
        return "feature_interaction_train_z_" + feature[len("feature_interaction_") :]
    return "feature_train_z_" + feature[len("feature_") :]


def centered_name(feature: str) -> str:
    return "feature_interaction_centered_" + feature[len("feature_interaction_") :]


def add_base_features(rows: list[dict[str, object]]) -> list[str]:
    required_names: list[str] = []
    for row in rows:
        for rich_col, candidate_col, out_col in REQUIRED_RICH_INTERACTIONS:
            value = finite_number(row.get(rich_col), 0.0) * finite_number(row.get(candidate_col), 0.0)
            row[out_col] = csv_number(value)
            if out_col not in required_names:
                required_names.append(out_col)
        for field in LOG1P_FIELDS:
            col = f"feature_rich_{field}"
            out_col = f"feature_rich_log1p_{field}"
            row[out_col] = csv_number(math.log1p(max(0.0, finite_number(row.get(col), 0.0))))
        for field, cap in CAP_FIELDS.items():
            col = f"feature_rich_{field}"
            out_col = f"feature_rich_capped_{field}"
            row[out_col] = csv_number(max(0.0, min(cap, finite_number(row.get(col), 0.0))))
    return required_names


def add_train_zscores(rows: list[dict[str, object]], features: list[str]) -> list[str]:
    train_rows = [row for row in rows if row.get("split") == "train"] or rows
    out_names = [train_z_name(feature) for feature in features]
    for feature, out_col in zip(features, out_names):
        values = [finite_number(row.get(feature), 0.0) for row in train_rows]
        mu = sum(values) / len(values) if values else 0.0
        var = sum((value - mu) ** 2 for value in values) / len(values) if values else 0.0
        sigma = math.sqrt(var)
        if sigma < 1.0e-12:
            sigma = 1.0
        for row in rows:
            row[out_col] = csv_number((finite_number(row.get(feature), 0.0) - mu) / sigma)
    return out_names


def add_centered_interactions(rows: list[dict[str, object]], features: list[str]) -> list[str]:
    out_names = [centered_name(feature) for feature in features]
    by_context = grouped_contexts(rows)
    for feature, out_col in zip(features, out_names):
        for group in by_context.values():
            values = [finite_number(row.get(feature), 0.0) for row in group]
            mu = sum(values) / len(values) if values else 0.0
            for row in group:
                row[out_col] = csv_number(finite_number(row.get(feature), 0.0) - mu)
    return out_names


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = [dict(row) for row in read_csv_rows(resolve(args.v4_csv, root))]
    required_interactions = add_base_features(rows)
    log_features = [f"feature_rich_log1p_{field}" for field in LOG1P_FIELDS]
    capped_features = [f"feature_rich_capped_{field}" for field in CAP_FIELDS]
    z_features = add_train_zscores(
        rows,
        [f"feature_rich_{field}" for field in LOG1P_FIELDS + list(CAP_FIELDS)] + required_interactions,
    )
    centered_features = add_centered_interactions(rows, required_interactions)

    features = feature_columns(rows)
    contexts = {str(row.get("normalized_context_key", "")) for row in rows}
    candidates = {str(row.get("candidate_id", "")) for row in rows}
    leak = leakage_scan(features)
    flags = observed_id_flags(rows)
    by_context = grouped_contexts(rows)
    candidate_counts = {key: len(group) for key, group in by_context.items()}
    rich_interaction_count = len([name for name in features if name.startswith("feature_interaction_rich_")])
    within_centered_count = len([name for name in features if name.startswith("feature_interaction_centered_")])
    gates = {
        "rows_eq_840": len(rows) == 840,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_14": len(candidates) == 14,
        "rich_interaction_feature_count_gt_0": rich_interaction_count > 0,
        "within_context_centered_feature_count_gt_0": within_centered_count > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "grouped_14_candidate_rows_per_context": all(count == 14 for count in candidate_counts.values()),
    }
    decision = "v5_interaction_feature_matrix_passed_continue_ranker" if all(gates.values()) else "v5_interaction_feature_matrix_gate_failed"
    summary = {
        "schema_version": "phase5p5_repair5g515_candidate_feature_matrix_v5_summary_v1",
        "decision": decision,
        "candidate_rows": len(rows),
        "contexts": len(contexts),
        "candidates": len(candidates),
        "feature_count": len(features),
        "required_rich_interaction_features": required_interactions,
        "rich_interaction_feature_count": rich_interaction_count,
        "within_context_centered_feature_count": within_centered_count,
        "train_only_zscore_feature_count": len(z_features),
        "log1p_count_feature_count": len(log_features),
        "capped_ratio_feature_count": len(capped_features),
        "ranking_feature_count": len(rank_feature_names(rows)),
        "context_only_gate_feature_count": len(context_only_rich_features(rows)),
        "candidate_varying_interaction_feature_count": count_candidate_varying(rows, interaction_feature_names(rows)),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "candidate_rows_per_context_min": min(candidate_counts.values()) if candidate_counts else 0,
        "candidate_rows_per_context_max": max(candidate_counts.values()) if candidate_counts else 0,
        "gates": gates,
        **flags,
        **G515_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), rows)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 Candidate Feature Matrix V5\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate_rows: `{len(rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidates: `{len(candidates)}`\n"
        f"- feature_count: `{len(features)}`\n"
        f"- rich_interaction_feature_count: `{rich_interaction_count}`\n"
        f"- within_context_centered_feature_count: `{within_centered_count}`\n"
        f"- train_only_zscore_feature_count: `{len(z_features)}`\n"
        f"- log1p_count_feature_count: `{len(log_features)}`\n"
        f"- capped_ratio_feature_count: `{len(capped_features)}`\n"
        f"- ranking_feature_count: `{summary['ranking_feature_count']}`\n"
        f"- context_only_gate_feature_count: `{summary['context_only_gate_feature_count']}`\n"
        f"- candidate_varying_interaction_feature_count: `{summary['candidate_varying_interaction_feature_count']}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "V5 keeps the G5.14 rows fixed and adds only runtime-safe rich trace by candidate-parameter interaction features, log/capped rich transforms, train-only z-score features, and within-context centered interaction features. "
        "No outcome, oracle, score, target, action, priority, restart, h-value, or candidate-deletion feature is added.\n",
    )
    print(json.dumps({"decision": decision, "candidate_rows": len(rows), "rich_interaction_feature_count": rich_interaction_count}))
    return 0 if decision != "v5_interaction_feature_matrix_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
