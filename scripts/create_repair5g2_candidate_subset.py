"""Create the Repair5G.2 flow-shield selector candidate subset."""

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

from create_repair5g1_agent_aware_dual_channel_candidates import build_candidates  # noqa: E402
from repair5g2_common import (  # noqa: E402
    G2_RANDOM_DIAGNOSTIC,
    G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC,
    G2_SHUFFLED_GOAL_DIAGNOSTIC,
    dirty_state,
    read_csv_rows,
    rel,
    repo_root,
    resolve,
    write_csv_rows,
)


DEFAULT_G1_RANKING = "outputs/tables/phase5p5_repair5g1_dev_candidate_ranking.csv"
DEFAULT_CSV = "outputs/tables/phase5p5_repair5g2_candidate_subset.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g2_candidate_subset_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g2_candidate_subset_summary.json"

CONTROL_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
]

C_EQUIV_BASELINES = [
    "repair5g_dual_c_equiv_c100_b125_w075_d100",
    "repair5g_dual_c_equiv_c125_b125_w075_d095",
    "repair5g_dual_c_equiv_c100_b100_w075_d095",
    "repair5g_dual_c_equiv_c100_b100_w075_d100",
    "repair5g_dual_c_equiv_c100_b100_w075_d090",
]

FLOW_SHIELD_BASES = [
    "c125_b125_w075_d095",
    "c100_b125_w075_d100",
    "c100_b100_w075_d095",
]
FLOW_SHIELD_BETAS = ["0p05", "0p1", "0p2", "0p35"]
FLOW_SHIELD_MAXES = ["0p25", "0p5", "0p75"]

AGENT_PROGRESS_METHODS = [
    "repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p75",
    "repair5g1_agent_c125_b125_w075_d095_lf0p05_min0p75",
    "repair5g1_agent_c100_b125_w075_d100_lf0p025_min0p75",
    "repair5g1_agent_c100_b125_w075_d100_lf0p05_min0p75",
    "repair5g1_agent_c100_b100_w075_d095_lf0p025_min0p75",
    "repair5g1_agent_c100_b100_w075_d095_lf0p05_min0p75",
]

SYNTHETIC_DIAGNOSTICS = [
    G2_RANDOM_DIAGNOSTIC,
    G2_SHUFFLED_GOAL_DIAGNOSTIC,
    G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC,
]


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def g1_candidate_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for candidate in build_candidates():
        row = candidate.__dict__.copy()
        out[str(candidate.runtime_method)] = row
    return out


def ranking_map(path: Path) -> dict[str, dict[str, str]]:
    return {str(row.get("method")): row for row in read_csv_rows(path)}


def base_row(
    *,
    runtime_method: str,
    component: str,
    role: str,
    source: str,
    g1_by_method: dict[str, dict[str, Any]],
    rank_by_method: dict[str, dict[str, str]],
    synthetic: bool = False,
) -> dict[str, Any]:
    g1 = g1_by_method.get(runtime_method, {})
    rank = rank_by_method.get(runtime_method, {})
    return {
        "runtime_method": runtime_method,
        "candidate_id": g1.get("candidate_id", runtime_method),
        "component": component,
        "g2_role": role,
        "source": source,
        "include_in_solver": not synthetic,
        "synthetic_diagnostic": synthetic,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "g1_rows": rank.get("rows", ""),
        "g1_better": rank.get("better", ""),
        "g1_equal": rank.get("equal", ""),
        "g1_worse": rank.get("worse", ""),
        "g1_mean_delta_ratio_vs_ltm": rank.get("mean_delta_ratio_vs_ltm", ""),
        "enable_dual_channel": g1.get("enable_dual_channel", ""),
        "goal_projection_mode": g1.get("goal_projection_mode", ""),
        "flow_shield_beta": g1.get("flow_shield_beta", ""),
        "max_flow_shield": g1.get("max_flow_shield", ""),
        "alpha_cong_commit_progress": g1.get("alpha_cong_commit_progress", ""),
        "alpha_cong_commit_nonprogress": g1.get("alpha_cong_commit_nonprogress", ""),
        "alpha_cong_block": g1.get("alpha_cong_block", ""),
        "alpha_cong_wait_progress": g1.get("alpha_cong_wait_progress", ""),
        "alpha_cong_wait_nonprogress": g1.get("alpha_cong_wait_nonprogress", ""),
        "rho_cong_decay": g1.get("rho_cong_decay", ""),
        "lambda_cong": g1.get("lambda_cong", ""),
        "lambda_flow": g1.get("lambda_flow", ""),
        "min_edge_cost": g1.get("min_edge_cost", ""),
        "max_edge_cost": g1.get("max_edge_cost", ""),
        "notes": g1.get("notes", ""),
    }


def build_subset(ranking_csv: Path) -> list[dict[str, Any]]:
    g1_by_method = g1_candidate_map()
    rank_by_method = ranking_map(ranking_csv)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(runtime_method: str, component: str, role: str, source: str, synthetic: bool = False) -> None:
        if runtime_method in seen:
            return
        seen.add(runtime_method)
        rows.append(
            base_row(
                runtime_method=runtime_method,
                component=component,
                role=role,
                source=source,
                g1_by_method=g1_by_method,
                rank_by_method=rank_by_method,
                synthetic=synthetic,
            )
        )

    for method in CONTROL_METHODS:
        add(method, "control", "control", "required_control")
    for method in C_EQUIV_BASELINES:
        add(method, "c_equiv_baseline", "c_equiv_baseline", "required_c_equiv")
    for base in FLOW_SHIELD_BASES:
        for beta in FLOW_SHIELD_BETAS:
            for max_shield in FLOW_SHIELD_MAXES:
                add(
                    f"repair5g1_shield_{base}_beta{beta}_max{max_shield}",
                    "flow_shield",
                    "flow_shield_family",
                    "required_flow_shield_grid",
                )
    for method in AGENT_PROGRESS_METHODS:
        add(method, "agent_progress_f", "agent_progress_diagnostic", "top_agent_progress_slice")
    add("repair5g1_random_static_diagnostic", "diagnostic", "deterministic_random_actual", "g1_actual_random_diagnostic")
    for method in SYNTHETIC_DIAGNOSTICS:
        add(method, "synthetic", "synthetic_diagnostic", "g2_synthesized_after_solver_rows", synthetic=True)
    return rows


def write_report(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Candidate Subset\n\n")
        handle.write("Diagnostic-only candidate subset for a non-leaky flow-shield selector protocol.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- final_ids_used: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n\n")
        handle.write("## Summary\n\n")
        handle.write(f"- rows: `{summary['candidate_subset_rows']}`\n")
        handle.write(f"- solver_methods: `{summary['solver_method_count']}`\n")
        handle.write(f"- synthetic_diagnostics: `{summary['synthetic_diagnostic_count']}`\n")
        handle.write(f"- component_counts: `{summary['component_counts']}`\n\n")
        handle.write("## Top Flow-Shield Carry-Forward\n\n")
        handle.write("| method | beta | max_shield | G1 better/equal/worse | G1 mean delta |\n")
        handle.write("|---|---:|---:|---:|---:|\n")
        for row in rows:
            if row["component"] != "flow_shield":
                continue
            handle.write(
                f"| `{row['runtime_method']}` | {row['flow_shield_beta']} | {row['max_flow_shield']} | "
                f"{row['g1_better']}/{row['g1_equal']}/{row['g1_worse']} | "
                f"{row['g1_mean_delta_ratio_vs_ltm']} |\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g1-ranking-csv", type=Path, default=Path(DEFAULT_G1_RANKING))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    ranking_csv = resolve(args.g1_ranking_csv, root)
    output_csv = resolve(args.output_csv, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    if not ranking_csv.exists():
        raise FileNotFoundError(ranking_csv)
    rows = build_subset(ranking_csv)
    fields = list(rows[0].keys()) if rows else []
    write_csv_rows(output_csv, rows, fields)
    component_counts = {
        component: sum(1 for row in rows if row["component"] == component)
        for component in sorted({row["component"] for row in rows})
    }
    summary = {
        "schema_version": "phase5p5_repair5g2_candidate_subset_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "candidate_subset_csv": rel(output_csv, root),
        "report": rel(report, root),
        "candidate_subset_rows": len(rows),
        "solver_method_count": sum(1 for row in rows if row["include_in_solver"]),
        "synthetic_diagnostic_count": sum(1 for row in rows if row["synthetic_diagnostic"]),
        "component_counts": component_counts,
        "runtime_methods": [row["runtime_method"] for row in rows],
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "final_ids_used": False,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary, rows)
    print(json.dumps({"rows": len(rows), "solver_methods": summary["solver_method_count"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
