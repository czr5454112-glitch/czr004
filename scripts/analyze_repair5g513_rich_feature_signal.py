"""Analyze Repair5G.5.13 rich feature signal when available."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import count_by, leakage_scan, read_csv_rows, read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g513_common import G513_CLOSED_CLAIMS  # noqa: E402


DEFAULT_MATRIX = "outputs/tables/phase5p5_repair5g513_rich_context_feature_matrix.csv"
DEFAULT_CREATE_SUMMARY = "outputs/reports/phase5p5_repair5g513_rich_context_feature_matrix_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g513_rich_feature_signal.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g513_rich_feature_signal_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rich-feature-csv", type=Path, default=Path(DEFAULT_MATRIX))
    parser.add_argument("--create-summary-json", type=Path, default=Path(DEFAULT_CREATE_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    create_summary = read_json(resolve(args.create_summary_json, root))
    rows = read_csv_rows(resolve(args.rich_feature_csv, root)) if resolve(args.rich_feature_csv, root).exists() else []
    feature_names = [name for name in rows[0] if name.startswith("feature_")] if rows else []
    rich_features = [name for name in feature_names if name.startswith("feature_rich_")]
    leak = leakage_scan(feature_names)
    if create_summary.get("decision") == "rich_context_features_missing_requires_local_feature_probe":
        decision = "rich_context_features_missing_requires_local_feature_probe"
        signal_ready = False
    elif rich_features and leak["forbidden_feature_count"] == 0:
        decision = "rich_feature_signal_inventory_ready"
        signal_ready = True
    else:
        decision = "rich_feature_signal_not_ready_continue_local_probe"
        signal_ready = False
    summary = {
        "schema_version": "phase5p5_repair5g513_rich_feature_signal_summary_v1",
        "decision": decision,
        "signal_ready": signal_ready,
        "rows": len(rows),
        "feature_count": len(feature_names),
        "rich_feature_count": len(rich_features),
        "rich_features": rich_features,
        "split_counts": count_by(rows, "split") if rows else {},
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "rich_vs_g512_ranker_rerun": "not_run_missing_rich_features" if not signal_ready else "not_run_inventory_only",
        "runtime_claim_allowed": False,
        **G513_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.13 Rich Feature Signal\n\n"
        f"- decision: `{decision}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- rich_feature_count: `{len(rich_features)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- rich_vs_g512_ranker_rerun: `{summary['rich_vs_g512_ranker_rerun']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The tracked artifacts do not provide enough rich pre-choice wait/block/progress fields for a valid rich-feature rerun when the decision is `rich_context_features_missing_requires_local_feature_probe`. "
        "The correct next step is a local observed-ID trace-feature probe with `--max-workers 1`, not a runtime-policy claim.\n",
    )
    print(json.dumps({"decision": decision, "rich_feature_count": len(rich_features)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
