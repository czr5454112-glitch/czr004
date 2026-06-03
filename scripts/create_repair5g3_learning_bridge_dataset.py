"""Create an offline Repair5G.3 contextual flow-shield selector dataset."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import (  # noqa: E402
    FLOW_SHIELD_NEARBY,
    git_value,
    load_json,
    map_defaults,
    number,
    read_csv_rows,
    read_jsonl,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
)


DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g3_learning_bridge_dataset.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g3_learning_bridge_dataset_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g3_learning_bridge_dataset_summary.json"

PAIRED_INPUTS = [
    ("g2_support", "outputs/tables/phase5p5_repair5g2_support_utility_long.csv"),
    ("g1_dev", "outputs/tables/phase5p5_repair5g1_dev_utility_long.csv"),
    ("g2_final_observed", "outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv"),
    ("g3_broader", "outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv"),
]

RAW_INPUTS = [
    "outputs/logs/phase5p5_repair5g2_support_probe/phase5p5_repair5g2_support_probe.jsonl",
    "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe.jsonl",
    "outputs/logs/phase5p5_repair5g2_fresh_final_eval/phase5p5_repair5g2_fresh_final_eval.jsonl",
    "outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation.jsonl",
]

ALLOWED_FEATURES = [
    "agents",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "free_cells",
    "density",
    "ltm_iterations",
    "returned_solutions_count_so_far",
    "has_incumbent_before",
    "best_ratio_before",
    "improved_last_iteration",
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "progress_committed_count",
    "nonprogress_committed_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "progress_ratio",
    "c_update_count",
    "f_update_count",
    "c_nonzero_edges",
    "f_nonzero_edges",
    "c_flow_update_ratio",
    "cost_min",
    "cost_max",
    "cost_span",
    "cost_bounds_respected",
]

FORBIDDEN_FEATURES = [
    "instance_id",
    "seed",
    "scen filename",
    "case key",
    "held-out candidate outcomes",
    "oracle label from the same held-out fold",
    "final solver outcome after the chosen update",
    "map-agent group lookup as the only decision rule",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(float(row.get("agents", 0) or 0)), int(float(row.get("seed", 0) or 0)))


def normalize_paired(row: dict[str, str], split: str) -> dict[str, Any]:
    method = row.get("candidate_id") or row.get("contender_method") or row.get("method") or ""
    return {
        "split_source": split,
        "map": row.get("map", ""),
        "agents": int(float(row.get("agents", 0) or 0)),
        "seed": int(float(row.get("seed", 0) or 0)),
        "method": method,
        "delta_ratio_vs_ltm": number(row.get("delta_ratio_vs_ltm") or row.get("delta_ratio"), math.nan),
        "success": str(row.get("success", row.get("contender_success", "true"))).lower() in {"true", "1", "yes"},
    }


def split_name(source: str, seed: int) -> str:
    if source == "g3_broader" and 66 <= seed <= 85:
        return "g3_broader_train"
    if source == "g3_broader" and 86 <= seed <= 105:
        return "g3_broader_validation"
    return source


def raw_feature_rows(root: Path) -> dict[tuple[str, int, int], dict[str, Any]]:
    out: dict[tuple[str, int, int], dict[str, Any]] = {}
    for raw_path in RAW_INPUTS:
        path = resolve(raw_path, root)
        for row in read_jsonl(path):
            if str(row.get("method")) != "lacam_star_ltm":
                continue
            out.setdefault(case_key(row), row)
    return out


def build_features(map_name: str, agents: int, raw: dict[str, Any] | None) -> dict[str, Any]:
    defaults = map_defaults(map_name, agents)
    committed = number(raw.get("committed_events") if raw else 0, 0.0)
    blocked = number(raw.get("blocked_events") if raw else 0, 0.0)
    wait_events = number(raw.get("repair5g_wait_progress_edges") if raw else 0, 0.0) + number(
        raw.get("repair5g_wait_nonprogress_edges") if raw else 0, 0.0
    )
    progress = number(raw.get("repair5g_committed_progress_events") if raw else 0, 0.0)
    nonprogress = number(raw.get("repair5g_committed_nonprogress_events") if raw else 0, 0.0)
    c_updates = number(raw.get("repair5g_congestion_update_count") if raw else 0, 0.0)
    f_updates = number(raw.get("repair5g_flow_update_count") if raw else 0, 0.0)
    c_nonzero = number(raw.get("repair5g_congestion_nonzero_edges") if raw else raw.get("nonzero_ltm_edges") if raw else 0, 0.0)
    f_nonzero = number(raw.get("repair5g_flow_nonzero_edges") if raw else 0, 0.0)
    cost_min = number(raw.get("repair5g_min_traversal_cost") if raw else 1.0, 1.0)
    cost_max = number(raw.get("repair5g_max_traversal_cost") if raw else 1.0, 1.0)
    return {
        **defaults,
        "ltm_iterations": number(raw.get("ltm_iterations") if raw else 0, 0.0),
        "returned_solutions_count_so_far": number(raw.get("returned_solutions_count") if raw else 0, 0.0),
        "has_incumbent_before": 0.0,
        "best_ratio_before": 0.0,
        "improved_last_iteration": 0.0,
        "committed_count": committed,
        "blocked_count": blocked,
        "wait_event_count": wait_events,
        "progress_committed_count": progress,
        "nonprogress_committed_count": nonprogress,
        "blocked_per_committed": blocked / committed if committed else 0.0,
        "wait_per_committed": wait_events / committed if committed else 0.0,
        "blocked_per_agent": blocked / agents if agents else 0.0,
        "committed_per_agent": committed / agents if agents else 0.0,
        "progress_ratio": progress / (progress + nonprogress) if (progress + nonprogress) else 0.0,
        "c_update_count": c_updates,
        "f_update_count": f_updates,
        "c_nonzero_edges": c_nonzero,
        "f_nonzero_edges": f_nonzero,
        "c_flow_update_ratio": c_updates / f_updates if f_updates else 0.0,
        "cost_min": cost_min,
        "cost_max": cost_max,
        "cost_span": cost_max - cost_min,
        "cost_bounds_respected": 1.0 if not raw or raw.get("repair5g_cost_bounds_respected", True) else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    raw_by_case = raw_feature_rows(root)
    paired: list[dict[str, Any]] = []
    for source, rel_path in PAIRED_INPUTS:
        path = resolve(rel_path, root)
        if not path.exists():
            continue
        paired.extend(normalize_paired(row, source) for row in read_csv_rows(path))
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in paired:
        key = (*case_key(row), split_name(str(row["split_source"]), int(row["seed"])))
        by_case.setdefault(key, {})[str(row["method"])] = row
    methods = sorted({row["method"] for row in paired if row["method"].startswith("repair5g1_shield_") or row["method"].startswith("repair5g_dual_c_equiv_") or row["method"] in {"repair5g2_frozen_static_or_selector", "repair5g2_best_frozen_static_candidate", "repair5g2_c_equiv_best_frozen_baseline"}})
    dataset: list[dict[str, Any]] = []
    for (map_name, agents, seed, split), outcomes in sorted(by_case.items()):
        useful = {method: row for method, row in outcomes.items() if method in methods}
        if not useful:
            continue
        best_method, best_row = min(useful.items(), key=lambda item: number(item[1].get("delta_ratio_vs_ltm"), math.inf))
        features = build_features(map_name, agents, raw_by_case.get((map_name, agents, seed)))
        row = {
            "split": split,
            "map": map_name,
            "agents": agents,
            "seed_metadata_only": seed,
            "best_method_label": best_method,
            "best_delta_ratio_vs_ltm": best_row.get("delta_ratio_vs_ltm"),
            "candidate_methods": json.dumps(sorted(useful), sort_keys=True),
            "runtime_feature_approximation": True,
            **features,
        }
        for method in methods:
            value = useful.get(method, {}).get("delta_ratio_vs_ltm")
            row[f"delta__{method}"] = value if value is not None else ""
        dataset.append(row)
    fields = [
        "split",
        "map",
        "agents",
        "seed_metadata_only",
        "best_method_label",
        "best_delta_ratio_vs_ltm",
        "candidate_methods",
        "runtime_feature_approximation",
        *ALLOWED_FEATURES,
        *[f"delta__{method}" for method in methods],
    ]
    write_csv_rows(resolve(args.output_csv, root), dataset, fields)
    split_counts = {split: sum(1 for row in dataset if row["split"] == split) for split in sorted({row["split"] for row in dataset})}
    summary = {
        "schema_version": "phase5p5_repair5g3_learning_bridge_dataset_summary_v1",
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dataset_csv": str(resolve(args.output_csv, root).relative_to(root)),
        "rows": len(dataset),
        "split_counts": split_counts,
        "candidate_methods": methods,
        "allowed_feature_names": ALLOWED_FEATURES,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
        "uses_no_forbidden_features": True,
        "runtime_feature_approximation": True,
        "reserved_learning_holdout": "IDs 106..125 preferred; unused by this dataset",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    report = resolve(args.report, root)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Phase5.5 Repair5G.3 Learning Bridge Dataset\n\n"
        "Offline contextual-selector dataset for bounded `UpdateLTM` parameter selection only.\n\n"
        f"- rows: `{len(dataset)}`\n"
        f"- split_counts: `{split_counts}`\n"
        "- forbidden runtime features used: `false`\n"
        "- runtime_feature_approximation: `true`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n",
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(dataset), "splits": split_counts}))
    return 0 if dataset else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
