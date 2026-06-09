"""Train Repair5G.5.9 corrected offline control models."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import (  # noqa: E402
    G59_CLOSED_STATUS,
    default_threshold_targets,
    feature_names_from_summary,
    is_true,
    load_json,
    missing_required_g58_artifacts,
    read_csv_rows,
    repo_root,
    resolve,
    row_split,
    stable_nonstatic_candidate,
    target_classes,
    train_multinomial_model,
    train_only_majority,
    train_only_map_agent_prior,
    training_rows,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g59_control_models/control_models.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_control_models_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_control_models_train_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-matrix-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURE_SUMMARY))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--seed", type=int, default=20260607)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    missing = missing_required_g58_artifacts(root)
    if missing:
        summary = {"decision": "missing_g58_artifacts_stop", "missing_artifacts": missing, **G59_CLOSED_STATUS}
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), "# Repair5G.5.9 Control Model Train\n\nmissing_g58_artifacts_stop\n")
        print(json.dumps({"decision": "missing_g58_artifacts_stop", "missing": len(missing)}))
        return 2

    feature_rows = read_csv_rows(resolve(args.feature_matrix_csv, root))
    feature_summary = load_json(resolve(args.feature_summary_json, root))
    feature_names = feature_names_from_summary(feature_summary, feature_rows)
    target_rows = default_threshold_targets(read_csv_rows(resolve(args.targets_csv, root)))
    targets_by_context = {row.get("context_id", ""): row for row in target_rows}
    merged = []
    for row in feature_rows:
        target = targets_by_context.get(row.get("context_id", ""))
        if target:
            merged.append({**row, **{key: target.get(key, row.get(key, "")) for key in target}})
    train_rows = [row for row in training_rows(merged) if row_split(row) == "train"]
    classes = target_classes(training_rows(merged))
    rng = random.Random(int(args.seed))
    shuffled_labels = [str(row.get("target_candidate_id", "")) for row in train_rows]
    rng.shuffle(shuffled_labels)
    real_model = train_multinomial_model(
        train_rows,
        feature_names,
        classes,
        label_field="target_candidate_id",
        seed=int(args.seed),
        salt="repair5g59_real_label_model",
    )
    random_feature_model = train_multinomial_model(
        train_rows,
        feature_names,
        classes,
        label_field="target_candidate_id",
        seed=int(args.seed) + 1,
        random_features=True,
        salt="repair5g59_true_random_feature_model",
    )
    shuffled_label_model = train_multinomial_model(
        train_rows,
        feature_names,
        classes,
        label_field="target_candidate_id",
        seed=int(args.seed) + 2,
        salt="repair5g59_true_shuffled_label_model",
        labels_override=shuffled_labels,
    )
    model = {
        "schema_version": "phase5p5_repair5g59_control_models_v1",
        "feature_names": feature_names,
        "classes": classes,
        "split_policy": "train_seed_le_150_dev_seed_gt_150_observed_only",
        "normalization": "train_rows_only",
        "train_rows": len(train_rows),
        "dev_rows": sum(1 for row in training_rows(merged) if row_split(row) == "dev"),
        "all_rows": len(merged),
        "training_eligible_rows": len(training_rows(merged)),
        "always_nonstatic_majority_candidate": stable_nonstatic_candidate(train_rows),
        "train_only_majority_candidate": train_only_majority(merged),
        "train_only_map_agent_prior": train_only_map_agent_prior(merged),
        "models": {
            "real_label_model": real_model,
            "true_random_feature_model": random_feature_model,
            "true_shuffled_label_model": shuffled_label_model,
        },
        "control_semantics": {
            "random_feature_model": "same train/dev split, same model class, deterministic random features, train-only normalization",
            "shuffled_label_model": "same train/dev split, same model class, train labels shuffled before fitting",
            "random_candidate": "candidate baseline only, not a random-feature trained model",
        },
        **G59_CLOSED_STATUS,
    }
    model_path = resolve(args.model_json, root)
    write_json(model_path, model)
    summary = {
        "schema_version": "phase5p5_repair5g59_control_models_train_summary_v1",
        "decision": "g59_corrected_control_models_trained",
        "model_json": str(model_path),
        "classes": classes,
        "feature_count": len(feature_names),
        "train_rows": len(train_rows),
        "dev_rows": model["dev_rows"],
        "normalization": "train_rows_only",
        "trained_controls": sorted(model["models"]),
        "previous_g58_naming_mismatch_recorded": True,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Corrected Control Model Train\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- train_rows: `{summary['train_rows']}`\n"
        f"- dev_rows: `{summary['dev_rows']}`\n"
        f"- feature_count: `{summary['feature_count']}`\n"
        f"- classes: `{json.dumps(classes)}`\n\n"
        "This creates true random-feature and shuffled-label trained controls without overwriting the original G5.8 summaries.\n",
    )
    print(json.dumps({"decision": summary["decision"], "train_rows": len(train_rows)}))
    return 0 if train_rows and classes else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
