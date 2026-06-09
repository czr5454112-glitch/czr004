"""Train a two-head Repair5G.5.9 abstention-aware offline policy."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import (  # noqa: E402
    G59_CLOSED_STATUS,
    G59_DEFAULT_MARGIN,
    default_threshold_targets,
    feature_names_from_summary,
    finite_number,
    load_json,
    read_csv_rows,
    repo_root,
    resolve,
    row_split,
    target_classes,
    train_multinomial_model,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g59_confidence_targets_v3.csv"
DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g59_abstention_aware_policy/policy.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_abstention_aware_offline_policy_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_abstention_aware_offline_policy_train_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-matrix-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURE_SUMMARY))
    parser.add_argument("--targets-v3-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--seed", type=int, default=20260607)
    return parser.parse_args(argv)


def merge_rows(feature_rows: list[dict[str, Any]], target_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets_by_context = {row.get("context_id", ""): row for row in target_rows}
    out = []
    for row in feature_rows:
        target = targets_by_context.get(row.get("context_id", ""))
        if target:
            out.append({**row, **{key: target.get(key, row.get(key, "")) for key in target}})
    return out


def default_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if abs(finite_number(row.get("margin_threshold"), math.nan) - G59_DEFAULT_MARGIN) < 1.0e-12]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    feature_rows = read_csv_rows(resolve(args.feature_matrix_csv, root))
    feature_summary = load_json(resolve(args.feature_summary_json, root))
    targets = default_targets(read_csv_rows(resolve(args.targets_v3_csv, root)))
    rows = merge_rows(feature_rows, targets)
    feature_names = feature_names_from_summary(feature_summary, rows)
    train_rows = [row for row in rows if row_split(row) == "train"]
    head_a_classes = sorted({str(row.get("head_a_class", "")) for row in train_rows if row.get("head_a_class")})
    head_b_train_rows = [row for row in train_rows if str(row.get("head_b_training_eligible", "")).lower() == "true"]
    head_b_classes = target_classes(head_b_train_rows)
    head_a_model = train_multinomial_model(
        train_rows,
        feature_names,
        head_a_classes,
        label_field="head_a_class",
        seed=int(args.seed),
        epochs=220,
        learning_rate=0.03,
        salt="repair5g59_head_a_feasibility_abstention",
    )
    head_b_model = train_multinomial_model(
        head_b_train_rows,
        feature_names,
        head_b_classes,
        label_field="head_b_target_candidate_id",
        seed=int(args.seed) + 1,
        epochs=220,
        learning_rate=0.03,
        salt="repair5g59_head_b_expert_selection",
    )
    model = {
        "schema_version": "phase5p5_repair5g59_abstention_aware_policy_v1",
        "policy_type": "two_head_calibrated_logistic_diagnostic",
        "feature_names": feature_names,
        "split_policy": "train_seed_le_150_dev_seed_gt_150_observed_only",
        "head_a": {
            "purpose": "feasibility/abstention/static-fallback routing",
            "classes": head_a_classes,
            "model": head_a_model,
        },
        "head_b": {
            "purpose": "expert selection only on stable eligible contexts",
            "classes": head_b_classes,
            "model": head_b_model,
        },
        "train_rows": len(train_rows),
        "head_b_train_rows": len(head_b_train_rows),
        "static_fallback_available": True,
        **G59_CLOSED_STATUS,
    }
    model_path = resolve(args.model_json, root)
    write_json(model_path, model)
    summary = {
        "schema_version": "phase5p5_repair5g59_abstention_aware_offline_policy_train_summary_v1",
        "decision": "abstention_aware_policy_trained_requires_eval",
        "model_json": str(model_path),
        "train_rows": len(train_rows),
        "head_a_classes": head_a_classes,
        "head_b_train_rows": len(head_b_train_rows),
        "head_b_classes": head_b_classes,
        "feature_count": len(feature_names),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Abstention-Aware Offline Policy Train\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- head_a_classes: `{json.dumps(head_a_classes)}`\n"
        f"- head_b_train_rows: `{len(head_b_train_rows)}`\n"
        f"- head_b_classes: `{json.dumps(head_b_classes)}`\n\n"
        "Head A trains feasibility/abstention routing; Head B trains expert selection only on stable eligible contexts.\n",
    )
    print(json.dumps({"decision": summary["decision"], "train_rows": len(train_rows)}))
    return 0 if train_rows and head_a_classes else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
