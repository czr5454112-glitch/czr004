"""Analyze feature signal and leakage status for G5.19 v8 features."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    G519_CLOSED_CLAIMS,
    G519_FEATURE_MATRIX_CSV,
    G519_FEATURE_SIGNAL_REPORT,
    G519_FEATURE_SIGNAL_SUMMARY,
    csv_number,
    finite_number,
    forbidden_feature_scan,
    matrix,
    perf_feature_columns,
    read_rows,
    target_array,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(G519_FEATURE_MATRIX_CSV))
    parser.add_argument("--report", type=Path, default=Path(G519_FEATURE_SIGNAL_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_FEATURE_SIGNAL_SUMMARY))
    return parser.parse_args(argv)


def abs_corr(x: np.ndarray, y: np.ndarray) -> float:
    if x.size == 0 or y.size == 0:
        return math.inf
    if float(np.std(x)) < 1.0e-12 or float(np.std(y)) < 1.0e-12:
        return 0.0
    return abs(float(np.corrcoef(x, y)[0, 1]))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = read_rows(args.feature_csv)
    features = perf_feature_columns(rows)
    y_delta = target_array(rows, "mean_delta_vs_static_primary")
    y_harm = np.array([1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= 0.005 else 0.0 for row in rows], dtype=float)
    X = matrix(rows, features)
    scored = []
    for index, feature in enumerate(features):
        scored.append(
            {
                "feature": feature,
                "abs_corr_delta": abs_corr(X[:, index], y_delta),
                "abs_corr_harmful": abs_corr(X[:, index], y_harm),
            }
        )
    top_delta = sorted(scored, key=lambda row: (-finite_number(row["abs_corr_delta"], 0), row["feature"]))[:15]
    top_harm = sorted(scored, key=lambda row: (-finite_number(row["abs_corr_harmful"], 0), row["feature"]))[:15]
    leak = forbidden_feature_scan(rows)
    groups = {
        "candidate_param_features": len([name for name in features if name.startswith("feature_candidate_")]),
        "rich_context_features": len([name for name in features if name.startswith("feature_rich_")]),
        "rich_x_candidate_interactions": len([name for name in features if name.startswith("feature_interaction_rich_")]),
        "within_context_centered_features": len([name for name in features if name.startswith("feature_centered_")]),
        "map_context_features": len([name for name in features if name.startswith("feature_map_")]),
    }
    gates = {
        "feature_count_gt_0": len(features) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "candidate_param_features_present": groups["candidate_param_features"] > 0,
        "rich_context_features_present": groups["rich_context_features"] > 0,
        "rich_x_candidate_interactions_present": groups["rich_x_candidate_interactions"] > 0,
        "within_context_centered_features_present": groups["within_context_centered_features"] > 0,
    }
    decision = "feature_signal_v8_passed_continue_ranker_suite" if all(gates.values()) else "feature_signal_v8_failed"
    summary = {
        "schema_version": "phase5p5_repair5g519_feature_signal_v8_summary_v1",
        "decision": decision,
        "rows": len(rows),
        "feature_count": len(features),
        "feature_groups": groups,
        "top_abs_corr_delta": top_delta,
        "top_abs_corr_harmful": top_harm,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **G519_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    delta_lines = "\n".join(
        f"- `{row['feature']}` corr_delta=`{csv_number(row['abs_corr_delta'])}` corr_harmful=`{csv_number(row['abs_corr_harmful'])}`"
        for row in top_delta[:10]
    )
    harm_lines = "\n".join(
        f"- `{row['feature']}` corr_harmful=`{csv_number(row['abs_corr_harmful'])}` corr_delta=`{csv_number(row['abs_corr_delta'])}`"
        for row in top_harm[:10]
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Feature Signal V8\n\n"
        f"- decision: `{decision}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- feature_count: `{len(features)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- feature_groups: `{groups}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## Delta Signal\n\n"
        f"{delta_lines}\n\n"
        "## Harmful Signal\n\n"
        f"{harm_lines}\n",
    )
    print(json.dumps({"decision": decision, "feature_count": len(features), "forbidden_feature_count": leak["forbidden_feature_count"]}))
    return 0 if decision != "feature_signal_v8_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
