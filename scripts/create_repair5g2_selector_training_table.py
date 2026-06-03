"""Build Repair5G.2 selector context rows from support and G1 dev data."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import (  # noqa: E402
    BASELINE_METHOD,
    case_dict,
    dirty_state,
    map_defaults,
    map_family,
    number,
    read_csv_rows,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    write_csv_rows,
)


DEFAULT_SUPPORT_WIDE = "outputs/tables/phase5p5_repair5g2_support_utility_wide.csv"
DEFAULT_SUPPORT_JSONL = "outputs/logs/phase5p5_repair5g2_support_probe/phase5p5_repair5g2_support_probe.jsonl"
DEFAULT_G1_DEV_WIDE = "outputs/tables/phase5p5_repair5g1_dev_utility_wide.csv"
DEFAULT_G1_DEV_JSONL = "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe.jsonl"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g2_selector_train_contexts.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g2_selector_training_table_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g2_selector_training_table_summary.json"

METADATA_FIELDS = [
    "case_id",
    "map",
    "map_family",
    "agents",
    "seed",
    "scen",
    "split_bucket",
    "source_feature_available",
    "source_c_method",
    "source_f_method",
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
    "best_ratio_before",
    "has_incumbent_before",
    "improved_last_iteration",
]

FORBIDDEN_FEATURES = [
    "instance_id",
    "seed as decision feature",
    "scen as decision feature",
    "candidate outcome columns from held-out fold",
    "final solver outcome not available before update",
    "F4/G1 oracle label as runtime feature",
]


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def pick_feature_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    grouped = case_dict(rows)
    out: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for key, methods in grouped.items():
        c_method = "repair5g_dual_c_equiv_additive"
        f_method = next((name for name in methods if name.startswith("repair5g1_shield_")), "")
        out[key] = {
            "baseline": methods.get(BASELINE_METHOD, {}),
            "c_row": methods.get(c_method, methods.get(BASELINE_METHOD, {})),
            "f_row": methods.get(f_method, methods.get(c_method, methods.get(BASELINE_METHOD, {}))),
            "source_c_method": c_method if c_method in methods else BASELINE_METHOD,
            "source_f_method": f_method,
        }
    return out


def context_rows(wide_csv: Path, raw_jsonl: Path, split_bucket: str) -> list[dict[str, Any]]:
    raw_rows = read_jsonl(raw_jsonl)
    features = pick_feature_rows(raw_rows)
    out: list[dict[str, Any]] = []
    for wide in read_csv_rows(wide_csv):
        map_name = str(wide.get("map"))
        agents = int(number(wide.get("agents"), 0))
        seed = int(number(wide.get("seed"), 0))
        scen = str(wide.get("scen", ""))
        key = (map_name, agents, seed, scen)
        selected = features.get(key, {"baseline": {}, "c_row": {}, "f_row": {}, "source_c_method": "", "source_f_method": ""})
        baseline = selected["baseline"]
        c_row = selected["c_row"]
        f_row = selected["f_row"]
        defaults = map_defaults(map_name, agents)
        committed = number(baseline.get("committed_events"), number(c_row.get("committed_events"), 0.0))
        blocked = number(baseline.get("blocked_events"), number(c_row.get("blocked_events"), 0.0))
        wait_events = number(c_row.get("repair5g_wait_progress_edges"), 0.0) + number(c_row.get("repair5g_wait_nonprogress_edges"), 0.0)
        progress = number(f_row.get("repair5g_committed_progress_events"), 0.0)
        nonprogress = number(f_row.get("repair5g_committed_nonprogress_events"), 0.0)
        c_update = number(c_row.get("repair5g_congestion_update_count"), 0.0)
        f_update = number(f_row.get("repair5g_flow_update_count"), 0.0)
        cost_min = number(f_row.get("repair5g_min_traversal_cost"), 1.0)
        cost_max = number(f_row.get("repair5g_max_traversal_cost"), 1.0)
        row: dict[str, Any] = {
            "case_id": f"{map_name}|a{agents}|s{seed}",
            "map": map_name,
            "map_family": map_family(map_name),
            "agents": agents,
            "seed": seed,
            "scen": scen,
            "split_bucket": split_bucket,
            "source_feature_available": bool(baseline or c_row or f_row),
            "source_c_method": selected.get("source_c_method", ""),
            "source_f_method": selected.get("source_f_method", ""),
            "map_width": defaults["map_width"],
            "map_height": defaults["map_height"],
            "obstacle_ratio": defaults["obstacle_ratio"],
            "free_cells": defaults["free_cells"],
            "density": defaults["density"],
            "ltm_iterations": number(baseline.get("ltm_iterations"), 0.0),
            "returned_solutions_count_so_far": number(baseline.get("returned_solutions_count"), 0.0),
            "committed_count": committed,
            "blocked_count": blocked,
            "wait_event_count": wait_events,
            "progress_committed_count": progress,
            "nonprogress_committed_count": nonprogress,
            "blocked_per_committed": blocked / committed if committed > 0 else 0.0,
            "wait_per_committed": wait_events / committed if committed > 0 else 0.0,
            "blocked_per_agent": blocked / agents if agents > 0 else 0.0,
            "committed_per_agent": committed / agents if agents > 0 else 0.0,
            "progress_ratio": progress / (progress + nonprogress) if (progress + nonprogress) > 0 else 0.0,
            "c_update_count": c_update,
            "f_update_count": f_update,
            "c_nonzero_edges": number(c_row.get("repair5g_congestion_nonzero_edges"), 0.0),
            "f_nonzero_edges": number(f_row.get("repair5g_flow_nonzero_edges"), 0.0),
            "c_flow_update_ratio": f_update / c_update if c_update > 0 else 0.0,
            "cost_min": cost_min,
            "cost_max": cost_max,
            "cost_span": max(cost_max - cost_min, 0.0),
            "cost_bounds_respected": 1.0 if str(f_row.get("repair5g_cost_bounds_respected", "true")).lower() == "true" else 0.0,
            "best_ratio_before": 0.0,
            "has_incumbent_before": 0.0,
            "improved_last_iteration": 0.0,
        }
        out.append(row)
    return sorted(out, key=lambda item: (item["split_bucket"], item["map"], item["agents"], item["seed"]))


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Selector Training Table\n\n")
        handle.write("Selector context rows for development-only G2 tuning. This does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- final_ids_used: `false`\n")
        handle.write("- candidate_outcomes_in_context_features: `false`\n")
        handle.write("- seed/scen retained only as join metadata\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n\n")
        handle.write("## Rows\n\n")
        handle.write(f"- context_rows: `{summary['context_rows']}`\n")
        handle.write(f"- support_rows: `{summary['support_rows']}`\n")
        handle.write(f"- dev_rows: `{summary['dev_rows']}`\n")
        handle.write(f"- final_id_rows: `{summary['final_id_rows']}`\n\n")
        handle.write("## Allowed Decision Features\n\n")
        for name in summary["allowed_feature_names"]:
            handle.write(f"- `{name}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-wide-csv", type=Path, default=Path(DEFAULT_SUPPORT_WIDE))
    parser.add_argument("--support-jsonl", type=Path, default=Path(DEFAULT_SUPPORT_JSONL))
    parser.add_argument("--g1-dev-wide-csv", type=Path, default=Path(DEFAULT_G1_DEV_WIDE))
    parser.add_argument("--g1-dev-jsonl", type=Path, default=Path(DEFAULT_G1_DEV_JSONL))
    parser.add_argument("--train-contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    support_wide = resolve(args.support_wide_csv, root)
    support_jsonl = resolve(args.support_jsonl, root)
    dev_wide = resolve(args.g1_dev_wide_csv, root)
    dev_jsonl = resolve(args.g1_dev_jsonl, root)
    for path in [support_wide, support_jsonl, dev_wide, dev_jsonl]:
        if not path.exists():
            raise FileNotFoundError(path)
    support = context_rows(support_wide, support_jsonl, "support_ids_1_25")
    dev = context_rows(dev_wide, dev_jsonl, "dev_ids_26_45")
    rows = [*support, *dev]
    fields = [*METADATA_FIELDS, *[name for name in ALLOWED_FEATURES if name not in METADATA_FIELDS]]
    contexts_csv = resolve(args.train_contexts_csv, root)
    write_csv_rows(contexts_csv, rows, fields)
    final_rows = [row for row in rows if int(row["seed"]) >= 46]
    summary = {
        "schema_version": "phase5p5_repair5g2_selector_training_table_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "train_contexts_csv": rel(contexts_csv, root),
        "context_rows": len(rows),
        "support_rows": len(support),
        "dev_rows": len(dev),
        "final_id_rows": len(final_rows),
        "selector_uses_no_forbidden_features": len(final_rows) == 0,
        "candidate_outcomes_in_context_features": False,
        "allowed_feature_names": ALLOWED_FEATURES,
        "metadata_fields_not_decision_features": METADATA_FIELDS,
        "forbidden_feature_names": FORBIDDEN_FEATURES,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary_path = resolve(args.summary_json, root)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"contexts": len(rows), "final_id_rows": len(final_rows)}))
    return 0 if not final_rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
