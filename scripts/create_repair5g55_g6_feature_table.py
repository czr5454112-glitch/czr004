"""Create a G6 feature table from Repair5G.5.5 pre-update checkpoints."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g54_common import G54_ALLOWED_RUNTIME_FEATURES  # noqa: E402
from repair5g55_common import (  # noqa: E402
    context_id_for,
    feature_values_from_checkpoint,
    read_jsonl,
    repo_root,
    resolve,
    validate_g55_instance_ids,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_CHECKPOINTS = "outputs/logs/phase5p5_repair5g55_scaled_counterfactual_labels/phase5p5_repair5g55_update_checkpoints.jsonl"
DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g55_g6_feature_table.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g55_g6_feature_table.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_g6_feature_table_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--feature-table-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    checkpoints = read_jsonl(resolve(args.checkpoint_jsonl, root))
    rows = []
    unexpected = set()
    for checkpoint in checkpoints:
        features = feature_values_from_checkpoint(checkpoint)
        unexpected.update(name for name in features if name not in G54_ALLOWED_RUNTIME_FEATURES)
        allowed_features = {name: value for name, value in features.items() if name in G54_ALLOWED_RUNTIME_FEATURES}
        rows.append(
            {
                "context_id": context_id_for(checkpoint),
                "map": checkpoint.get("map", ""),
                "agents": checkpoint.get("agents", ""),
                "seed": checkpoint.get("seed", ""),
                "iteration": checkpoint.get("iteration", ""),
                "traffic_before_hash_full": checkpoint.get("traffic_before_hash_full", ""),
                "trace_event_count": checkpoint.get("trace_event_count", ""),
                "feature_count": len(allowed_features),
                **allowed_features,
            }
        )
    observed_only = True
    try:
        validate_g55_instance_ids([int(row.get("seed", 0)) for row in rows], label="Repair5G.5.5 feature rows")
    except SystemExit:
        observed_only = False
    write_csv_rows(resolve(args.feature_table_csv, root), rows)
    feature_columns = sorted({key for row in rows for key in row if key in G54_ALLOWED_RUNTIME_FEATURES})
    gates = {
        "feature_rows_gt_0": len(rows) > 0,
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
        "feature_columns_nonempty": bool(feature_columns),
        "only_allowed_runtime_features_exported": not unexpected,
        "metadata_not_model_features": True,
    }
    gates["g6_feature_table_created"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g55_g6_feature_table_summary_v1",
        "feature_rows": len(rows),
        "feature_columns": feature_columns,
        "unexpected_feature_names": sorted(unexpected),
        "feature_table_csv": str(resolve(args.feature_table_csv, root)),
        "gates": gates,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "g6_training_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.5 G6 Feature Table\n\n"
        f"- feature_rows: `{len(rows)}`\n"
        f"- feature_columns: `{json.dumps(feature_columns)}`\n"
        f"- only_allowed_runtime_features_exported: `{gates['only_allowed_runtime_features_exported']}`\n"
        f"- g6_feature_table_created: `{gates['g6_feature_table_created']}`\n\n"
        "The CSV keeps context identifiers and traffic hashes as audit metadata. The model feature set is limited to allowed pre-update runtime features.\n",
    )
    print(json.dumps({"g6_feature_table_created": gates["g6_feature_table_created"], "feature_rows": len(rows)}))
    return 0 if gates["g6_feature_table_created"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
