"""Train Repair5G.5.10 abstention-aware parameter-lattice policy if gates pass."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, context_key, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g59_common import train_multinomial_model  # noqa: E402


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g510_feature_matrix_v2.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g510_confidence_targets_v4.csv"
DEFAULT_TARGET_SUMMARY = "outputs/reports/phase5p5_repair5g510_confidence_targets_v4_summary.json"
DEFAULT_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g510_feature_signal_v2_summary.json"
DEFAULT_ANALYSIS_SUMMARY = "outputs/reports/phase5p5_repair5g510_lattice_counterfactual_analysis_summary.json"
DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g510_abstention_parameter_policy/policy.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_train_summary.json"
METADATA = {"context_id", "normalized_context_key", "map", "agents", "seed", "iteration", "traffic_before_hash_full"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--target-summary-json", type=Path, default=Path(DEFAULT_TARGET_SUMMARY))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURE_SUMMARY))
    parser.add_argument("--analysis-summary-json", type=Path, default=Path(DEFAULT_ANALYSIS_SUMMARY))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def gates_pass(target_summary: dict[str, object], feature_summary: dict[str, object], analysis_summary: dict[str, object]) -> tuple[bool, list[str]]:
    reasons = []
    if target_summary.get("decision") != "confidence_targets_v4_passed_policy_training_allowed":
        reasons.append("confidence_targets_v4_training_gate_failed")
    if not feature_summary.get("features_strong_enough_to_distinguish_static_vs_nonstatic_safely"):
        reasons.append("feature_signal_v2_failed_continue_feature_design")
    if not analysis_summary.get("candidate_space_improves_g58"):
        reasons.append("candidate_space_gap_expand_flow_shield_lattice")
    return not reasons, reasons


def is_true(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def row_split(row: dict[str, object]) -> str:
    try:
        return "train" if int(float(row.get("seed") or 0)) <= 150 else "dev"
    except (TypeError, ValueError):
        return "train"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    target_summary = load_json(resolve(args.target_summary_json, root))
    feature_summary = load_json(resolve(args.feature_summary_json, root))
    analysis_summary = load_json(resolve(args.analysis_summary_json, root))
    allowed, reasons = gates_pass(target_summary, feature_summary, analysis_summary)
    model_path = resolve(args.model_json, root)
    if not allowed:
        summary = {
            "schema_version": "phase5p5_repair5g510_abstention_parameter_policy_train_summary_v1",
            "decision": "abstention_parameter_policy_training_skipped_gate_failed",
            "training_skipped": True,
            "blocked_reasons": reasons,
            "model_json": "",
            **G59_CLOSED_STATUS,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(
            resolve(args.report, root),
            "# Phase5.5 Repair5G.5.10 Abstention Parameter Policy Train\n\n"
            f"- decision: `{summary['decision']}`\n"
            f"- blocked_reasons: `{reasons}`\n\n"
            "The policy is not trained because G5.10 gates did not pass. This preserves the no-learned-method-claim rule.\n",
        )
        print(json.dumps({"decision": summary["decision"], "blocked_reasons": reasons}))
        return 0

    features = {context_key(row): row for row in read_csv_rows(resolve(args.feature_csv, root))}
    targets = read_csv_rows(resolve(args.targets_csv, root))
    rows = []
    for target in targets:
        if not is_true(target.get("training_eligible")):
            continue
        feat = features.get(context_key(target))
        if feat is None:
            continue
        rows.append({**feat, **target})
    train_rows = [row for row in rows if row_split(row) == "train"]
    feature_names = sorted(key for row in rows for key in row if key not in METADATA and not key.startswith("_") and key not in {"label_class", "target_candidate_id", "training_eligible", "head_a_target", "head_b_target_candidate_id", "train_weight", "confidence_margin", "confidence_reason"})
    head_a_classes = sorted({str(row.get("head_a_target", "")) for row in train_rows if row.get("head_a_target")})
    head_b_classes = sorted({str(row.get("head_b_target_candidate_id", "")) for row in train_rows if row.get("head_b_target_candidate_id")})
    model = {
        "schema_version": "phase5p5_repair5g510_abstention_parameter_policy_v1",
        "feature_names": feature_names,
        "head_a": train_multinomial_model(train_rows, feature_names, head_a_classes, label_field="head_a_target", seed=20260607, salt="repair5g510_head_a"),
        "head_b": train_multinomial_model(train_rows, feature_names, head_b_classes, label_field="head_b_target_candidate_id", seed=20260608, salt="repair5g510_head_b"),
        "policy_scope": "offline_observed_dev_only",
        **G59_CLOSED_STATUS,
    }
    write_json(model_path, model)
    summary = {
        "schema_version": "phase5p5_repair5g510_abstention_parameter_policy_train_summary_v1",
        "decision": "abstention_parameter_policy_trained_offline",
        "training_skipped": False,
        "training_rows": len(train_rows),
        "all_rows": len(rows),
        "feature_count": len(feature_names),
        "head_a_classes": head_a_classes,
        "head_b_classes": head_b_classes,
        "model_json": str(model_path),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(resolve(args.report, root), "# Phase5.5 Repair5G.5.10 Abstention Parameter Policy Train\n\nPolicy trained offline after all G5.10 gates passed.\n")
    print(json.dumps({"decision": summary["decision"], "training_rows": len(train_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
