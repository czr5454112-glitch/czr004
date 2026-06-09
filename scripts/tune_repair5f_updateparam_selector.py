"""Tune conservative Repair5F.2 bounded UpdateParams selectors on support data."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5f_selector_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    ALLOWED_FEATURES,
    FORBIDDEN_FEATURES,
    SelectorSpec,
    apply_selector,
    attach_realized_outcomes,
    feature_stats,
    load_utility_long,
    metrics_for_realized,
    read_csv_rows,
    write_csv_rows,
)


DEFAULT_SUPPORT_LONG = "outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv"
DEFAULT_TRAIN_CONTEXTS = "outputs/tables/phase5p5_repair5f_selector_train_contexts.csv"
DEFAULT_SWEEP_CSV = "outputs/tables/phase5p5_repair5f_selector_threshold_sweep.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_selector_threshold_sweep_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_threshold_sweep_summary.json"
DEFAULT_SPEC = "outputs/reports/phase5p5_repair5f_selector_spec.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def bool_pass(metrics: dict[str, Any]) -> bool:
    mean_delta = metrics.get("mean_delta_ratio_vs_ltm")
    return (
        int(metrics.get("better") or 0) > int(metrics.get("worse") or 0)
        and mean_delta is not None
        and float(mean_delta) < 0.0
        and int(metrics.get("ratio_worse_than_ltm_groups") or 0) <= 1
        and int(metrics.get("success_worse_than_ltm_groups") or 0) == 0
        and int(metrics.get("selected_nonadditive_cases") or 0) > 0
    )


def candidate_specs() -> list[SelectorSpec]:
    specs: list[SelectorSpec] = []
    selector_types = [
        "knn_utility",
        "radius_neighbor_abstain",
        "group_balanced_utility",
        "candidate_risk_capped",
    ]
    configs = [
        {
            "min_support_count": 5,
            "min_effective_neighbors": 3,
            "max_neighbor_distance": 1.5,
            "min_predicted_margin": 0.0,
            "max_candidate_worse_rate": 0.5,
            "max_group_worse_rate": 0.5,
            "non_additive_budget": 1.0,
        },
        {
            "min_support_count": 10,
            "min_effective_neighbors": 3,
            "max_neighbor_distance": 999.0,
            "min_predicted_margin": 0.001,
            "max_candidate_worse_rate": 1.0,
            "max_group_worse_rate": 1.0,
            "non_additive_budget": 1.0,
        },
        {
            "min_support_count": 20,
            "min_effective_neighbors": 5,
            "max_neighbor_distance": 999.0,
            "min_predicted_margin": 0.003,
            "max_candidate_worse_rate": 0.25,
            "max_group_worse_rate": 0.0,
            "non_additive_budget": 0.5,
        },
    ]
    for selector_type in selector_types:
        for config in configs:
            specs.append(
                SelectorSpec(
                    selector_type=selector_type,
                    min_support_count=int(config["min_support_count"]),
                    min_effective_neighbors=int(config["min_effective_neighbors"]),
                    max_neighbor_distance=float(config["max_neighbor_distance"]),
                    min_predicted_margin=float(config["min_predicted_margin"]),
                    max_candidate_worse_rate=float(config["max_candidate_worse_rate"]),
                    max_group_worse_rate=float(config["max_group_worse_rate"]),
                    additive_fallback_threshold=float(config["min_predicted_margin"]),
                    non_additive_budget=float(config["non_additive_budget"]),
                )
            )
    return specs


def evaluate_spec(
    *,
    spec: SelectorSpec,
    contexts: list[dict[str, Any]],
    utility_by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    decisions = apply_selector(
        contexts=contexts,
        support_contexts=contexts,
        utility_by_case=utility_by_case,
        feature_names=ALLOWED_FEATURES,
        spec=spec,
        leave_one_out=True,
    )
    realized = attach_realized_outcomes(decisions, utility_by_case)
    metrics = metrics_for_realized(realized)
    return realized, metrics


def sweep_row(spec: SelectorSpec, metrics: dict[str, Any]) -> dict[str, Any]:
    passed = bool_pass(metrics)
    return {
        **spec.as_dict(),
        "min_fold_agreement": 0,
        "support_rows": metrics.get("rows"),
        "better": metrics.get("better"),
        "equal": metrics.get("equal"),
        "worse": metrics.get("worse"),
        "better_minus_worse": int(metrics.get("better") or 0) - int(metrics.get("worse") or 0),
        "mean_delta_ratio_vs_ltm": metrics.get("mean_delta_ratio_vs_ltm"),
        "ratio_worse_than_ltm_groups": metrics.get("ratio_worse_than_ltm_groups"),
        "success_worse_than_ltm_groups": metrics.get("success_worse_than_ltm_groups"),
        "zero_nonadditive_groups": metrics.get("zero_nonadditive_groups"),
        "selected_nonadditive_cases": metrics.get("selected_nonadditive_cases"),
        "additive_fallback_cases": metrics.get("additive_fallback_cases"),
        "additive_fallback_rate": metrics.get("additive_fallback_rate"),
        "support_primary_passed": passed,
        "selected_candidate_distribution": json.dumps(metrics.get("selected_candidate_distribution"), sort_keys=True),
    }


def rank_row(row: dict[str, Any]) -> tuple[Any, ...]:
    mean_delta = row.get("mean_delta_ratio_vs_ltm")
    if mean_delta is None or not math.isfinite(float(mean_delta)):
        mean_delta = 999.0
    return (
        not bool(row.get("support_primary_passed")),
        float(mean_delta),
        -int(row.get("better_minus_worse") or 0),
        int(row.get("ratio_worse_than_ltm_groups") or 999),
        float(row.get("additive_fallback_rate") or 1.0),
        str(row.get("selector_type")),
    )


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    best = summary["best_support_selector"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Selector Threshold Sweep\n\n")
        handle.write("This sweep is trained/tuned only on support IDs. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- support_only_tuning: `true`\n")
        handle.write("- final_holdout_used_for_tuning: `false`\n\n")
        handle.write("## Best Support Spec\n\n")
        for key in [
            "selector_type",
            "min_support_count",
            "min_effective_neighbors",
            "max_neighbor_distance",
            "min_predicted_margin",
            "max_candidate_worse_rate",
            "max_group_worse_rate",
            "non_additive_budget",
            "support_primary_passed",
            "better",
            "equal",
            "worse",
            "mean_delta_ratio_vs_ltm",
            "selected_nonadditive_cases",
        ]:
            handle.write(f"- {key}: `{best.get(key)}`\n")
        handle.write("\n## Selector Families\n\n")
        handle.write("- `knn_utility`\n")
        handle.write("- `radius_neighbor_abstain`\n")
        handle.write("- `group_balanced_utility`\n")
        handle.write("- `candidate_risk_capped`\n\n")
        handle.write("## Feature Policy\n\n")
        handle.write("The selected spec uses only the allowed numeric feature list from the training-context table. ")
        handle.write("Seed, scenario name, instance identity, holdout outcomes, and holdout best-candidate columns are forbidden.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-long-csv", type=Path, default=Path(DEFAULT_SUPPORT_LONG))
    parser.add_argument("--train-contexts-csv", type=Path, default=Path(DEFAULT_TRAIN_CONTEXTS))
    parser.add_argument("--sweep-csv", type=Path, default=Path(DEFAULT_SWEEP_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SPEC))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    support_long = resolve(args.support_long_csv, root)
    train_contexts_csv = resolve(args.train_contexts_csv, root)
    sweep_csv = resolve(args.sweep_csv, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    selector_spec_json = resolve(args.selector_spec_json, root)
    for path in [support_long, train_contexts_csv]:
        if not path.exists():
            raise FileNotFoundError(path)

    contexts = read_csv_rows(train_contexts_csv)
    utility_by_case = load_utility_long(support_long)
    rows: list[dict[str, Any]] = []
    best_realized: list[dict[str, Any]] = []
    for spec in candidate_specs():
        realized, metrics = evaluate_spec(spec=spec, contexts=contexts, utility_by_case=utility_by_case)
        row = sweep_row(spec, metrics)
        rows.append(row)
        if not best_realized or rank_row(row) < rank_row(rows[0]):
            best_realized = realized
    rows.sort(key=rank_row)
    best = rows[0]
    best_spec = SelectorSpec.from_mapping(best)
    best_realized, best_metrics = evaluate_spec(
        spec=best_spec,
        contexts=contexts,
        utility_by_case=utility_by_case,
    )
    fields = [
        "selector_type",
        "min_support_count",
        "min_effective_neighbors",
        "max_neighbor_distance",
        "min_predicted_margin",
        "max_candidate_worse_rate",
        "max_group_worse_rate",
        "min_fold_agreement",
        "non_additive_budget",
        "additive_fallback_threshold",
        "support_rows",
        "better",
        "equal",
        "worse",
        "better_minus_worse",
        "mean_delta_ratio_vs_ltm",
        "ratio_worse_than_ltm_groups",
        "success_worse_than_ltm_groups",
        "zero_nonadditive_groups",
        "selected_nonadditive_cases",
        "additive_fallback_cases",
        "additive_fallback_rate",
        "support_primary_passed",
        "selected_candidate_distribution",
    ]
    write_csv_rows(sweep_csv, rows, fields)

    spec_payload = {
        "schema_version": "phase5p5_repair5f_selector_spec_v1",
        "created_at": datetime.now().isoformat(),
        "selector_method": "repair5f_support_trained_selector_simulation",
        "selector_spec": best_spec.as_dict(),
        "support_metrics": best_metrics,
        "support_only_tuning": True,
        "final_holdout_used_for_tuning": False,
        "allowed_feature_names": ALLOWED_FEATURES,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
        "feature_stats": feature_stats(contexts, ALLOWED_FEATURES),
        "support_long_csv": str(support_long),
        "train_contexts_csv": str(train_contexts_csv),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "selected_support_decisions_preview": best_realized[:20],
    }
    selector_spec_json.parent.mkdir(parents=True, exist_ok=True)
    selector_spec_json.write_text(json.dumps(spec_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "schema_version": "phase5p5_repair5f_selector_threshold_sweep_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "support_only_tuning": True,
        "final_holdout_used_for_tuning": False,
        "support_long_csv": str(support_long),
        "train_contexts_csv": str(train_contexts_csv),
        "sweep_csv": str(sweep_csv),
        "report": str(report),
        "summary_json": str(summary_json),
        "selector_spec_json": str(selector_spec_json),
        "sweep_rows": len(rows),
        "support_context_rows": len(contexts),
        "best_support_selector": best,
        "best_selector_spec": best_spec.as_dict(),
        "best_support_metrics": best_metrics,
        "additive_candidate_id": ADDITIVE_CANDIDATE,
        "allowed_feature_names": ALLOWED_FEATURES,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"sweep_csv": str(sweep_csv), "selector_spec_json": str(selector_spec_json)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
