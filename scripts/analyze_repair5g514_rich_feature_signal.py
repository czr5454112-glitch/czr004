"""Analyze G5.14 rich feature signal and v3/v4 feature inventory."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import finite_number, leakage_scan, mean, read_csv_rows, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g514_common import DEFAULT_V4_MATRIX, G514_CLOSED_CLAIMS, all_rich_feature_columns  # noqa: E402


DEFAULT_V3 = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_SIGNAL_CSV = "outputs/tables/phase5p5_repair5g514_rich_feature_signal.csv"
DEFAULT_INVENTORY_CSV = "outputs/tables/phase5p5_repair5g514_v4_feature_inventory.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_rich_feature_signal.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_rich_feature_signal_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v3-csv", type=Path, default=Path(DEFAULT_V3))
    parser.add_argument("--v4-csv", type=Path, default=Path(DEFAULT_V4_MATRIX))
    parser.add_argument("--signal-csv", type=Path, default=Path(DEFAULT_SIGNAL_CSV))
    parser.add_argument("--inventory-csv", type=Path, default=Path(DEFAULT_INVENTORY_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def corr(xs: list[float], ys: list[float]) -> float:
    finite = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(finite) < 3:
        return math.nan
    x = np.array([item[0] for item in finite], dtype=float)
    y = np.array([item[1] for item in finite], dtype=float)
    if float(x.std()) < 1.0e-12 or float(y.std()) < 1.0e-12:
        return math.nan
    return float(np.corrcoef(x, y)[0, 1])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    v3_rows = read_csv_rows(resolve(args.v3_csv, root))
    v4_rows = read_csv_rows(resolve(args.v4_csv, root))
    v3_features = {name for name in v3_rows[0] if name.startswith("feature_")} if v3_rows else set()
    v4_features = {name for name in v4_rows[0] if name.startswith("feature_")} if v4_rows else set()
    rich_features = [name for name in sorted(v4_features) if name in set(all_rich_feature_columns())]
    target_delta = [finite_number(row.get("mean_delta_vs_static_primary"), math.nan) for row in v4_rows]
    target_harm = [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= 0.005 else 0.0 for row in v4_rows]

    signal_rows = []
    for feature in rich_features:
        values = [finite_number(row.get(feature), math.nan) for row in v4_rows]
        signal_rows.append(
            {
                "row_type": "rich_feature_correlation",
                "feature_name": feature,
                "pearson_corr_delta_vs_static": corr(values, target_delta),
                "pearson_corr_harmful": corr(values, target_harm),
                "unique_values": len({round(value, 12) for value in values if math.isfinite(value)}),
                "mean_value": mean(values),
            }
        )

    by_map_agent: dict[str, set[tuple[float, ...]]] = defaultdict(set)
    for row in v4_rows:
        key = f"{row.get('map', '')}|a{row.get('agents', '')}"
        signature = tuple(finite_number(row.get(name), math.nan) for name in rich_features)
        by_map_agent[key].add(signature)
    leakage_rows = [
        {
            "row_type": "map_agent_leakage_suspicion",
            "map_agent": key,
            "unique_rich_signatures": len(signatures),
        }
        for key, signatures in sorted(by_map_agent.items())
    ]
    signal_rows.extend(leakage_rows)

    inventory_rows = []
    for feature in sorted(v3_features | v4_features):
        if feature.startswith("feature_rich_"):
            group = "rich_context"
        elif feature.startswith("feature_candidate_"):
            group = "candidate_param"
        elif feature.startswith("feature_interaction_"):
            group = "interaction"
        elif feature.startswith("feature_map_"):
            group = "context_v3"
        else:
            group = "other"
        inventory_rows.append(
            {
                "feature_name": feature,
                "feature_group": group,
                "present_in_v3": feature in v3_features,
                "present_in_v4": feature in v4_features,
                "included_in_perf_safe_model": feature in v4_features,
            }
        )

    leak = leakage_scan(v4_features)
    missing_contexts = len({row.get("normalized_context_key", "") for row in v4_rows if row.get("rich_context_feature_present") not in {True, "True", "true", "1"}})
    top_delta = sorted(
        [row for row in signal_rows if row["row_type"] == "rich_feature_correlation" and math.isfinite(finite_number(row["pearson_corr_delta_vs_static"], math.nan))],
        key=lambda row: abs(finite_number(row["pearson_corr_delta_vs_static"], 0.0)),
        reverse=True,
    )[:5]
    decision = "rich_feature_signal_analyzed_continue_v4_ranker" if rich_features and leak["forbidden_feature_count"] == 0 else "rich_feature_signal_analysis_gate_failed"
    summary = {
        "schema_version": "phase5p5_repair5g514_rich_feature_signal_summary_v1",
        "decision": decision,
        "candidate_rows": len(v4_rows),
        "contexts": len({row.get("normalized_context_key", "") for row in v4_rows}),
        "v3_feature_count": len(v3_features),
        "v4_feature_count": len(v4_features),
        "rich_feature_count": len(rich_features),
        "missing_rich_contexts": missing_contexts,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "top_abs_delta_correlations": top_delta,
        "map_agent_leakage_suspicion": {
            "map_agent_groups": len(by_map_agent),
            "groups_with_one_rich_signature": sum(1 for signatures in by_map_agent.values() if len(signatures) == 1),
            "note": "A single signature per map-agent would be suspicious; multiple signatures per group indicate the recovered rich fields vary by context.",
        },
        "rich_only_model_sanity": {
            "status": "reported_by_eval_script",
            "note": "The eval script trains a rich-only grouped ranker control and reports it beside v4.",
        },
        **G514_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.signal_csv, root), signal_rows)
    write_csv_rows(resolve(args.inventory_csv, root), inventory_rows)
    write_json(resolve(args.summary_json, root), summary)
    top_lines = "\n".join(
        f"- `{row['feature_name']}`: corr_delta={finite_number(row['pearson_corr_delta_vs_static'], math.nan):.4f}, corr_harm={finite_number(row['pearson_corr_harmful'], math.nan):.4f}"
        for row in top_delta
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Rich Feature Signal\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate_rows: `{len(v4_rows)}`\n"
        f"- rich_feature_count: `{len(rich_features)}`\n"
        f"- missing_rich_contexts: `{missing_contexts}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- map_agent_leakage_suspicion: `{summary['map_agent_leakage_suspicion']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## Top Rich Feature Correlations\n\n"
        f"{top_lines or '- none'}\n\n"
        "The correlations are diagnostic only; the grouped hard-control evaluation decides whether v4 actually beats simple priors.\n",
    )
    print(json.dumps({"decision": decision, "rich_feature_count": len(rich_features), "missing_contexts": missing_contexts}))
    return 0 if decision != "rich_feature_signal_analysis_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
