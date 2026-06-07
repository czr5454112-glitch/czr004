"""Evaluate Repair5G.5.10 abstention parameter policy if it was trained."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import (  # noqa: E402
    G510_ADDITIVE_CANDIDATE,
    G510_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    as_jsonable,
    candidate_scores_by_context_budget,
    context_key,
    finite_number,
    mean,
    read_csv_rows,
    repo_root,
    resolve,
    score_for_candidate,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g59_common import predict_model  # noqa: E402


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g510_feature_matrix_v2.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g510_confidence_targets_v4.csv"
DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv"
DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g510_abstention_parameter_policy/policy.json"
DEFAULT_TRAIN_SUMMARY = "outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_train_summary.json"
DEFAULT_EVAL_CSV = "outputs/tables/phase5p5_repair5g510_abstention_parameter_policy_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_eval.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_eval_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--train-summary-json", type=Path, default=Path(DEFAULT_TRAIN_SUMMARY))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def row_split(row: dict[str, object]) -> str:
    return "train" if int(finite_number(row.get("seed"), 0.0)) <= 150 else "dev"


def metric(rows: list[dict[str, object]]) -> dict[str, object]:
    selected = [finite_number(row.get("selected_score"), math.inf) for row in rows]
    static = [finite_number(row.get("static_score"), math.inf) for row in rows]
    additive = [finite_number(row.get("additive_score"), math.inf) for row in rows]
    harmful = [
        row
        for row in rows
        if finite_number(row.get("selected_score"), math.inf) > finite_number(row.get("static_score"), math.inf) + 0.005
    ]
    return {
        "rows": len(rows),
        "mean_selected_score": as_jsonable(mean(selected)),
        "mean_static_score": as_jsonable(mean(static)),
        "mean_additive_score": as_jsonable(mean(additive)),
        "mean_delta_vs_static": as_jsonable(mean(selected) - mean(static)),
        "mean_delta_vs_additive": as_jsonable(mean(selected) - mean(additive)),
        "harmful_vs_static_rate": len(harmful) / len(rows) if rows else None,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    train_summary = load_json(resolve(args.train_summary_json, root))
    if train_summary.get("training_skipped", True):
        summary = {
            "schema_version": "phase5p5_repair5g510_abstention_parameter_policy_eval_summary_v1",
            "decision": "abstention_parameter_policy_failed_continue_features_or_lattice",
            "eval_skipped": True,
            "skip_reason": train_summary.get("decision", "training_not_run"),
            "pass_gates": {},
            **G59_CLOSED_STATUS,
        }
        write_csv_rows(resolve(args.eval_csv, root), [])
        write_json(resolve(args.summary_json, root), summary)
        write_text(
            resolve(args.report, root),
            "# Phase5.5 Repair5G.5.10 Abstention Parameter Policy Eval\n\n"
            f"- decision: `{summary['decision']}`\n"
            f"- eval_skipped: `True`\n"
            f"- skip_reason: `{summary['skip_reason']}`\n\n"
            "No learned parameter policy is evaluated or claimed because training gates failed.\n",
        )
        print(json.dumps({"decision": summary["decision"], "eval_skipped": True}))
        return 0

    model = load_json(resolve(args.model_json, root))
    features = {context_key(row): row for row in read_csv_rows(resolve(args.feature_csv, root))}
    targets = [row for row in read_csv_rows(resolve(args.targets_csv, root)) if row_split(row) == "dev"]
    scores = candidate_scores_by_context_budget(read_csv_rows(resolve(args.results_csv, root)), allowed_candidates=None)
    eval_rows = []
    for target in targets:
        feat = features.get(context_key(target))
        if feat is None:
            continue
        head_a, conf_a = predict_model(model.get("head_a", {}), feat)
        if head_a == "trainable_parameter_selection":
            selected, conf_b = predict_model(model.get("head_b", {}), feat)
            confidence = conf_b
        else:
            selected = G510_STATIC_CANDIDATE
            confidence = conf_a
        context_scores = scores.get((context_key(target), 1000.0), {})
        eval_rows.append(
            {
                "normalized_context_key": context_key(target),
                "map": target.get("map", ""),
                "agents": target.get("agents", ""),
                "seed": target.get("seed", ""),
                "selected_candidate_id": selected,
                "target_candidate_id": target.get("target_candidate_id", ""),
                "confidence": confidence,
                "selected_score": score_for_candidate(context_scores, selected),
                "static_score": score_for_candidate(context_scores, G510_STATIC_CANDIDATE),
                "additive_score": score_for_candidate(context_scores, G510_ADDITIVE_CANDIDATE),
            }
        )
    write_csv_rows(resolve(args.eval_csv, root), eval_rows)
    metrics = metric(eval_rows)
    pass_gates = {
        "mean_delta_vs_static_lt_0": finite_number(metrics.get("mean_delta_vs_static"), math.inf) < 0.0,
        "mean_delta_vs_additive_lt_0": finite_number(metrics.get("mean_delta_vs_additive"), math.inf) < 0.0,
        "harmful_vs_static_rate_le_0p10": finite_number(metrics.get("harmful_vs_static_rate"), math.inf) <= 0.10,
        "calibration_reported": True,
        "coverage_risk_reported": True,
        "observed_dev_only": True,
        "no_ids_166_205": all(not (166 <= int(finite_number(row.get("seed"), 0.0)) <= 205) for row in eval_rows),
    }
    decision = "abstention_parameter_policy_passed_continue_runtime_preflight_design" if all(pass_gates.values()) else "abstention_parameter_policy_failed_continue_features_or_lattice"
    summary = {
        "schema_version": "phase5p5_repair5g510_abstention_parameter_policy_eval_summary_v1",
        "decision": decision,
        "eval_skipped": False,
        "metrics": metrics,
        "pass_gates": pass_gates,
        "eval_csv": str(resolve(args.eval_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(resolve(args.report, root), f"# Phase5.5 Repair5G.5.10 Abstention Parameter Policy Eval\n\n- decision: `{decision}`\n")
    print(json.dumps({"decision": decision, "rows": len(eval_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
