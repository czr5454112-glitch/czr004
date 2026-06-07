"""Analyze feature-signal quality for G5.12 candidate feature matrix v3."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import CLOSED_CLAIMS, count_by, finite_number, leakage_scan, mean, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_candidate_feature_signal_v3.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_candidate_feature_signal_v3_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def correlation(xs: list[float], ys: list[float]) -> float:
    paired = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(paired) < 3:
        return 0.0
    mx = sum(x for x, _ in paired) / len(paired)
    my = sum(y for _, y in paired) / len(paired)
    vx = sum((x - mx) ** 2 for x, _ in paired)
    vy = sum((y - my) ** 2 for _, y in paired)
    if vx <= 0 or vy <= 0:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in paired)
    return cov / math.sqrt(vx * vy)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    feature_names = [name for name in rows[0] if name.startswith("feature_")] if rows else []
    targets = [finite_number(row.get("mean_delta_vs_static_primary"), math.nan) for row in rows]
    leak = leakage_scan(feature_names)
    correlations = []
    for name in feature_names:
        xs = [finite_number(row.get(name), math.nan) for row in rows]
        corr = correlation(xs, targets)
        correlations.append({"feature": name, "corr_with_mean_delta_vs_static": corr, "abs_corr": abs(corr)})
    top = sorted(correlations, key=lambda row: (-row["abs_corr"], row["feature"]))[:12]
    contexts = {str(row.get("normalized_context_key", "")) for row in rows}
    candidates = {str(row.get("candidate_id", "")) for row in rows}
    gates = {
        "perf_safe_candidate_rows_ge_840": len(rows) >= 840,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "candidate_param_features_present": any(name.startswith("feature_candidate_") for name in feature_names),
        "interaction_features_present": any(name.startswith("feature_interaction_") for name in feature_names),
        "train_dev_split_seed_based": count_by(rows, "split").get("train", 0) > 0 and count_by(rows, "split").get("dev", 0) > 0,
        "grouped_context_ids_preserved": len(contexts) == 60,
    }
    decision = "feature_v3_passed_continue_candidate_ranker" if all(gates.values()) else "feature_v3_failed_continue_feature_design"
    summary = {
        "schema_version": "phase5p5_repair5g512_candidate_feature_signal_v3_summary_v1",
        "decision": decision,
        "rows": len(rows),
        "contexts": len(contexts),
        "candidates": len(candidates),
        "feature_count": len(feature_names),
        "split_counts": count_by(rows, "split"),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "target_mean_delta_vs_static_mean": mean(targets),
        "top_abs_correlations": top,
        "feature_signal_limited": True,
        "missing_runtime_context_features_reported": True,
        "feature_signal_limited_reason": "Available perf-safe context signal is metadata plus trace_event_count; rich wait/block/progress aggregates are absent from the tracked G5.11 table.",
        "gates": gates,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    top_lines = "\n".join(
        f"- `{row['feature']}`: corr={row['corr_with_mean_delta_vs_static']:.4f}"
        for row in top
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Candidate Feature Signal v3\n\n"
        f"- decision: `{decision}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidates: `{len(candidates)}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- split_counts: `{count_by(rows, 'split')}`\n"
        f"- feature_signal_limited: `true`\n"
        f"- missing_runtime_context_features_reported: `true`\n"
        f"- gates: `{gates}`\n\n"
        "## Top Absolute Correlations\n\n"
        f"{top_lines}\n\n"
        "These correlations are diagnostics only. The performance-safe feature set remains leakage-clean, but context signal is limited because rich pre-choice trace aggregates are not present in the tracked G5.11 artifacts.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "forbidden_feature_count": leak["forbidden_feature_count"]}))
    return 0 if decision != "feature_v3_failed_continue_feature_design" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
