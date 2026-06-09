"""Evaluate the Repair5F.2 support-trained selector on final holdout tables."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5f_selector_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    ALLOWED_FEATURES,
    SELECTOR_METHOD,
    SelectorSpec,
    apply_selector,
    attach_realized_outcomes,
    case_key,
    correlation_rows,
    load_utility_long,
    metrics_for_realized,
    per_group_breakdown,
    read_csv_rows,
    read_jsonl,
    write_csv_rows,
)


DEFAULT_SPEC = "outputs/reports/phase5p5_repair5f_selector_spec.json"
DEFAULT_SUPPORT_LONG = "outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv"
DEFAULT_TRAIN_CONTEXTS = "outputs/tables/phase5p5_repair5f_selector_train_contexts.csv"
DEFAULT_HOLDOUT_LONG = "outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_long.csv"
DEFAULT_HOLDOUT_WIDE = "outputs/tables/phase5p5_repair5f_updateparam_utility_rerun_wide.csv"
DEFAULT_HOLDOUT_CONTEXTS = "outputs/tables/phase5p5_repair5f_selector_holdout_contexts.csv"
DEFAULT_HOLDOUT_RAW = (
    "outputs/logs/phase5p5_repair5f_candidate_probe_rerun/"
    "phase5p5_repair5f_candidate_probe_rerun.jsonl"
)
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5f_selector_simulation_paired.csv"
DEFAULT_DECISIONS = "outputs/tables/phase5p5_repair5f_selector_simulation_decisions.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_selector_simulation_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_simulation_summary.json"
DEFAULT_RUNTIME_RECOMMENDATION = "outputs/reports/phase5p5_repair5f_selector_runtime_export_recommendation.md"


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


def num(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def metric_rows_from_deltas(rows: list[dict[str, Any]], candidate_label: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        delta = num(row.get("delta"), 0.0)
        out.append(
            {
                "case_id": row.get("case_id", ""),
                "map": row["map"],
                "agents": int(row["agents"]),
                "seed": int(row["seed"]),
                "scen": row.get("scen", ""),
                "selected_candidate_id": row.get("candidate_id", candidate_label),
                "realized_delta_ratio_vs_ltm": delta,
                "realized_success": True,
                "better_vs_ltm": delta < -1.0e-12,
                "equal_vs_ltm": abs(delta) <= 1.0e-12,
                "worse_vs_ltm": delta > 1.0e-12,
            }
        )
    return out


def comparator_rows_from_wide(wide_csv: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv_rows(wide_csv):
        base = num(row.get("lacam_star_ltm_ratio"))
        common = {
            "case_id": f"{row.get('map')}|a{int(num(row.get('agents'), 0))}|s{int(num(row.get('seed'), 0))}",
            "map": row.get("map", ""),
            "agents": int(num(row.get("agents"), 0)),
            "seed": int(num(row.get("seed"), 0)),
            "scen": row.get("scen", ""),
        }
        out["always_additive_defer"].append({**common, "candidate_id": ADDITIVE_CANDIDATE, "delta": 0.0})
        out["repair5f_candidate_additive_ltm"].append({**common, "candidate_id": ADDITIVE_CANDIDATE, "delta": 0.0})
        e5_ratio = num(row.get("repair5e5_ratio"))
        if math.isfinite(base) and math.isfinite(e5_ratio):
            out["repair5e5_crossfold_utility_reranker"].append(
                {**common, "candidate_id": "repair5e5", "delta": e5_ratio - base}
            )
        for method in [
            "repair5f_candidate_lattice_oracle_static_proxy",
            "repair5f_bounded_updateparam_selector_random_candidate_diagnostic",
            "repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic",
        ]:
            delta = num(row.get(f"{method}_delta_ratio_vs_ltm"))
            candidate = row.get(f"{method}_candidate_id") or method
            if math.isfinite(delta):
                out[method].append({**common, "candidate_id": candidate, "delta": delta})
    return dict(out)


def comparator_rows_from_raw(raw_jsonl: Path) -> dict[str, list[dict[str, Any]]]:
    rows = read_jsonl(raw_jsonl)
    by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_case[case_key(row)][str(row.get("method"))] = row
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, methods in by_case.items():
        base = methods.get("lacam_star_ltm")
        if base is None:
            continue
        base_ratio = num(base.get("sum_of_loss_ratio"))
        if not math.isfinite(base_ratio):
            continue
        common = {
            "case_id": f"{key[0]}|a{key[1]}|s{key[2]}",
            "map": key[0],
            "agents": key[1],
            "seed": key[2],
            "scen": base.get("scen", ""),
        }
        for method in [
            "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic",
        ]:
            row = methods.get(method)
            if row is None:
                continue
            ratio = num(row.get("sum_of_loss_ratio"))
            if math.isfinite(ratio):
                out[method].append({**common, "candidate_id": method, "delta": ratio - base_ratio})
    return dict(out)


def support_realized_risk(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["selected_candidate_id"])].append(num(row.get("realized_delta_ratio_vs_ltm"), 0.0))
    out: dict[str, dict[str, Any]] = {}
    for candidate, deltas in sorted(grouped.items()):
        out[candidate] = {
            "rows": len(deltas),
            "mean_delta_ratio_vs_ltm": sum(deltas) / len(deltas) if deltas else None,
            "worse_rate": sum(1 for value in deltas if value > 1.0e-12) / len(deltas) if deltas else None,
        }
    return out


def pass_gates(selector: dict[str, Any], comparators: dict[str, dict[str, Any]], leakage: bool) -> dict[str, bool]:
    selector_mean = selector.get("mean_delta_ratio_vs_ltm")
    random_mean = comparators.get("repair5f_bounded_updateparam_selector_random_candidate_diagnostic", {}).get(
        "mean_delta_ratio_vs_ltm"
    )
    shuffled_mean = comparators.get("repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic", {}).get(
        "mean_delta_ratio_vs_ltm"
    )
    e5_mean = comparators.get("repair5e5_crossfold_utility_reranker", {}).get("mean_delta_ratio_vs_ltm")
    return {
        "support_final_leakage_false": not leakage,
        "selector_better_gt_worse": int(selector.get("better") or 0) > int(selector.get("worse") or 0),
        "selector_mean_delta_lt_0": selector_mean is not None and float(selector_mean) < 0.0,
        "selector_ratio_worse_groups_le_1": int(selector.get("ratio_worse_than_ltm_groups") or 0) <= 1,
        "selector_success_worse_groups_eq_0": int(selector.get("success_worse_than_ltm_groups") or 0) == 0,
        "selector_beats_random_candidate_diagnostic": (
            selector_mean is not None and random_mean is not None and float(selector_mean) < float(random_mean)
        ),
        "selector_beats_shuffled_utility_diagnostic": (
            selector_mean is not None and shuffled_mean is not None and float(selector_mean) < float(shuffled_mean)
        ),
        "selector_improves_over_e5_real_selector": (
            selector_mean is not None and e5_mean is not None and float(selector_mean) < float(e5_mean)
        ),
        "selector_does_not_collapse_to_additive": int(selector.get("selected_nonadditive_cases") or 0) > 0,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selector = summary["selector_metrics"]
    gates = summary["table_simulation_pass_gates"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Selector Simulation\n\n")
        handle.write("This is a table-level final-holdout simulation. It does not export a runtime artifact.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- final_holdout_used_for_tuning: `false`\n\n")
        handle.write("## Selector Metrics\n\n")
        for key in [
            "rows",
            "better",
            "equal",
            "worse",
            "mean_delta_ratio_vs_ltm",
            "ratio_worse_than_ltm_groups",
            "success_worse_than_ltm_groups",
            "selected_nonadditive_cases",
            "additive_fallback_rate",
        ]:
            handle.write(f"- {key}: `{selector.get(key)}`\n")
        handle.write("\n## Pass Gates\n\n")
        for key, value in gates.items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write(f"\nOverall table simulation passed: `{summary['table_simulation_passed']}`\n\n")
        handle.write("## Comparator Means\n\n")
        handle.write("| method | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|\n")
        for method, row in sorted(summary["comparator_metrics"].items()):
            handle.write(
                f"| `{method}` | {row.get('better')} | {row.get('equal')} | {row.get('worse')} | "
                f"{row.get('mean_delta_ratio_vs_ltm')} |\n"
            )
        handle.write("\n## Runtime Recommendation\n\n")
        if summary["table_simulation_passed"]:
            handle.write(
                "The table-level selector simulation passes the F2 gates. A follow-up runtime export can be planned, "
                "but no runtime artifact is exported by this script.\n"
            )
        else:
            handle.write(
                "The table-level selector simulation does not pass all F2 gates. Runtime export remains blocked.\n"
            )


def write_runtime_recommendation(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selector = summary["selector_metrics"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Repair5F.2 Runtime Export Recommendation\n\n")
        handle.write("This follow-up report is created because the table-level selector simulation passed. ")
        handle.write("It recommends a scoped runtime-export task, but no runtime artifact is exported here.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- runtime_export_created: `false`\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n\n")
        handle.write("## Evidence To Carry Forward\n\n")
        handle.write(f"- selector method: `{summary['selector_method']}`\n")
        handle.write(f"- selected candidate distribution: `{summary['selected_candidate_distribution']}`\n")
        handle.write(f"- better / equal / worse: `{selector['better']} / {selector['equal']} / {selector['worse']}`\n")
        handle.write(f"- mean_delta_ratio_vs_ltm: `{selector['mean_delta_ratio_vs_ltm']}`\n")
        handle.write(f"- ratio_worse_than_ltm_groups: `{selector['ratio_worse_than_ltm_groups']}`\n")
        handle.write(f"- success_worse_than_ltm_groups: `{selector['success_worse_than_ltm_groups']}`\n")
        handle.write(f"- support_final_overlap_count: `{summary['support_final_overlap_count']}`\n\n")
        handle.write("## Recommended Next Task\n\n")
        handle.write("Create `scripts/create_repair5f_updateparam_selector_runtime.py` and ")
        handle.write("`artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/` in a separate scoped step. ")
        handle.write("The first runtime should select one bounded candidate at the first eligible post-first-solution update, ")
        handle.write("lock that candidate for the run, log the selected UpdateParams, and preserve exact additive fallback.\n\n")
        handle.write("## Required Runtime Gates\n\n")
        handle.write("- force-additive parity exact\n")
        handle.write("- exact additive candidate parity exact\n")
        handle.write("- runtime selector reproduces the table-level decision policy\n")
        handle.write("- actual runtime better > worse\n")
        handle.write("- actual runtime mean_delta_ratio_vs_ltm < 0\n")
        handle.write("- actual runtime ratio_worse_than_ltm_groups <= 1\n")
        handle.write("- actual runtime success_worse_than_ltm_groups = 0\n")
        handle.write("- random/shuffled diagnostics remain weaker\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SPEC))
    parser.add_argument("--support-long-csv", type=Path, default=Path(DEFAULT_SUPPORT_LONG))
    parser.add_argument("--train-contexts-csv", type=Path, default=Path(DEFAULT_TRAIN_CONTEXTS))
    parser.add_argument("--holdout-long-csv", type=Path, default=Path(DEFAULT_HOLDOUT_LONG))
    parser.add_argument("--holdout-wide-csv", type=Path, default=Path(DEFAULT_HOLDOUT_WIDE))
    parser.add_argument("--holdout-contexts-csv", type=Path, default=Path(DEFAULT_HOLDOUT_CONTEXTS))
    parser.add_argument("--holdout-raw-jsonl", type=Path, default=Path(DEFAULT_HOLDOUT_RAW))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--decisions-csv", type=Path, default=Path(DEFAULT_DECISIONS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--runtime-recommendation-report", type=Path, default=Path(DEFAULT_RUNTIME_RECOMMENDATION))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    selector_spec_json = resolve(args.selector_spec_json, root)
    support_long = resolve(args.support_long_csv, root)
    train_contexts_csv = resolve(args.train_contexts_csv, root)
    holdout_long = resolve(args.holdout_long_csv, root)
    holdout_wide = resolve(args.holdout_wide_csv, root)
    holdout_contexts_csv = resolve(args.holdout_contexts_csv, root)
    holdout_raw = resolve(args.holdout_raw_jsonl, root)
    paired_csv = resolve(args.paired_csv, root)
    decisions_csv = resolve(args.decisions_csv, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    runtime_recommendation = resolve(args.runtime_recommendation_report, root)
    for path in [selector_spec_json, support_long, train_contexts_csv, holdout_long, holdout_wide, holdout_contexts_csv]:
        if not path.exists():
            raise FileNotFoundError(path)

    spec_payload = json.loads(selector_spec_json.read_text(encoding="utf-8"))
    spec = SelectorSpec.from_mapping(spec_payload["selector_spec"])
    support_contexts = read_csv_rows(train_contexts_csv)
    holdout_contexts = read_csv_rows(holdout_contexts_csv)
    support_utility = load_utility_long(support_long)
    holdout_utility = load_utility_long(holdout_long)
    decisions = apply_selector(
        contexts=holdout_contexts,
        support_contexts=support_contexts,
        utility_by_case=support_utility,
        feature_names=ALLOWED_FEATURES,
        spec=spec,
        leave_one_out=False,
    )
    paired = attach_realized_outcomes(decisions, holdout_utility)

    decision_fields = [
        "case_id",
        "map",
        "map_family",
        "agents",
        "seed",
        "scen",
        "selected_candidate_id",
        "decision_status",
        "fallback_reason",
        "support_count",
        "effective_neighbors",
        "nearest_distance",
        "predicted_delta_ratio",
        "predicted_margin_ratio",
        "candidate_worse_rate",
        "group_worse_rate",
    ]
    paired_fields = [
        *decision_fields,
        "realized_delta_ratio_vs_ltm",
        "realized_success",
        "better_vs_ltm",
        "equal_vs_ltm",
        "worse_vs_ltm",
    ]
    write_csv_rows(decisions_csv, decisions, decision_fields)
    write_csv_rows(paired_csv, paired, paired_fields)

    selector_metrics = metrics_for_realized(paired)
    comparators_raw = comparator_rows_from_wide(holdout_wide)
    if holdout_raw.exists():
        for method, rows in comparator_rows_from_raw(holdout_raw).items():
            comparators_raw[method] = rows
    comparator_metrics = {
        method: metrics_for_realized(metric_rows_from_deltas(rows, method))
        for method, rows in sorted(comparators_raw.items())
    }
    support_cases = {case_key(row) for row in support_contexts}
    holdout_cases = {case_key(row) for row in holdout_contexts}
    leakage = bool(support_cases & holdout_cases)
    gates = pass_gates(selector_metrics, comparator_metrics, leakage)
    passed = all(gates.values())
    selector_metrics["candidate_specific_realized_risk"] = support_realized_risk(paired)
    selector_metrics.update(correlation_rows(paired))

    summary = {
        "schema_version": "phase5p5_repair5f_selector_simulation_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "solver_semantic_changes": False,
        "selector_method": SELECTOR_METHOD,
        "selector_spec_json": str(selector_spec_json),
        "selector_spec": spec.as_dict(),
        "support_long_csv": str(support_long),
        "train_contexts_csv": str(train_contexts_csv),
        "holdout_long_csv": str(holdout_long),
        "holdout_wide_csv": str(holdout_wide),
        "holdout_contexts_csv": str(holdout_contexts_csv),
        "paired_csv": str(paired_csv),
        "decisions_csv": str(decisions_csv),
        "report": str(report),
        "summary_json": str(summary_json),
        "runtime_recommendation_report": str(runtime_recommendation),
        "support_final_overlap_count": len(support_cases & holdout_cases),
        "support_final_overlap_examples": [
            {"map": item[0], "agents": item[1], "seed": item[2]} for item in sorted(support_cases & holdout_cases)[:20]
        ],
        "final_holdout_used_for_tuning": False,
        "selector_metrics": selector_metrics,
        "comparator_metrics": comparator_metrics,
        "table_simulation_pass_gates": gates,
        "table_simulation_passed": passed,
        "map_agent_breakdown": per_group_breakdown(paired),
        "selected_candidate_distribution": dict(Counter(row["selected_candidate_id"] for row in paired)),
        "runtime_export_recommended": passed,
        "runtime_export_created": False,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    if passed:
        write_runtime_recommendation(runtime_recommendation, summary)
    print(json.dumps({"paired_csv": str(paired_csv), "summary_json": str(summary_json), "passed": passed}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
