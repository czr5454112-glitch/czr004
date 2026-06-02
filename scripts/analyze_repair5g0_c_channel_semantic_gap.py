"""Analyze the Repair5G.0 C-channel scalar semantic gap."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_G0_SUMMARY_JSON = "outputs/reports/phase5p5_repair5g_dual_channel_dev_probe_summary.json"
DEFAULT_G0_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g_dual_channel_dev_summary.csv"
DEFAULT_G0_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g_dual_channel_dev_by_map_agent.csv"
DEFAULT_F4_RANKING = "outputs/tables/phase5p5_repair5f4_full_lattice_static_candidate_ranking.csv"
DEFAULT_LTM_CPP = "cpp/ltm/ltm.cpp"
DEFAULT_LTM_HPP = "cpp/ltm/ltm.hpp"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g0_c_channel_semantic_gap.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g0_c_channel_semantic_gap_summary.json"
G0_COMMIT = "85636b4"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def git_show(path: str, root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "show", f"{G0_COMMIT}:{path.replace(chr(92), '/')}"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def find_row(rows: list[dict[str, str]], value: str, *, key: str = "method") -> dict[str, Any]:
    for row in rows:
        if row.get(key) == value:
            return row
    return {}


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze_code(g0_cpp: str, current_cpp: str, current_hpp: str) -> dict[str, Any]:
    g0_committed_block = ""
    g0_progress_block = ""
    progress_marker = "if (has_progress_info && progress > 0.0)"
    if progress_marker in g0_cpp:
        progress_start = g0_cpp.find(progress_marker)
        g0_committed_block = g0_cpp[max(0, progress_start - 120): progress_start + 900]
        else_marker = "\n    } else {"
        progress_end = g0_cpp.find(else_marker, progress_start)
        if progress_end == -1:
            progress_end = progress_start + 450
        g0_progress_block = g0_cpp[progress_start:progress_end]
    current_has_fix = "alpha_cong_commit_progress" in current_cpp and "alpha_cong_commit_progress" in current_hpp
    return {
        "g0_code_available": bool(g0_cpp),
        "g0_committed_progress_block_mentions_flow_update": "increment_flow_edge" in g0_progress_block,
        "g0_committed_progress_block_mentions_congestion_update": "increment_edge" in g0_progress_block,
        "g0_committed_progress_updates_only_flow": (
            bool(g0_progress_block)
            and "increment_flow_edge" in g0_progress_block
            and "increment_edge" not in g0_progress_block
        ),
        "current_code_has_alpha_cong_commit_progress": current_has_fix,
        "g0_progress_block_excerpt": "\n".join(g0_progress_block.splitlines()[:18]),
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    g0_summary = read_json(resolve(args.g0_summary_json, root))
    dev_rows = read_csv(resolve(args.g0_summary_csv, root))
    f4_rows = read_csv(resolve(args.f4_ranking_csv, root))
    current_cpp = resolve(args.ltm_cpp, root).read_text(encoding="utf-8")
    current_hpp = resolve(args.ltm_hpp, root).read_text(encoding="utf-8")
    g0_cpp = git_show("cpp/ltm/ltm.cpp", root) or current_cpp

    scalar_best = find_row(dev_rows, "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only")
    dual_best = find_row(dev_rows, "repair5g_dual_c_only_best_f4_observed")
    scalar_locked = find_row(dev_rows, "repair5f_static_c100_b100_w075_d090")
    dual_locked = find_row(dev_rows, "repair5g_dual_c_only_locked_f4")
    f4_best = find_row(f4_rows, "c125_b125_w075_d095", key="candidate_id")

    scalar_best_mean = to_float(scalar_best.get("mean_delta_ratio_vs_ltm"))
    dual_best_mean = to_float(dual_best.get("mean_delta_ratio_vs_ltm"))
    scalar_locked_mean = to_float(scalar_locked.get("mean_delta_ratio_vs_ltm"))
    dual_locked_mean = to_float(dual_locked.get("mean_delta_ratio_vs_ltm"))

    code = analyze_code(g0_cpp, current_cpp, current_hpp)
    c_only_ignored_progress = bool(code["g0_committed_progress_updates_only_flow"])
    best_gap = (
        dual_best_mean - scalar_best_mean
        if scalar_best_mean is not None and dual_best_mean is not None
        else None
    )
    locked_gap = (
        dual_locked_mean - scalar_locked_mean
        if scalar_locked_mean is not None and dual_locked_mean is not None
        else None
    )
    explains_mismatch = c_only_ignored_progress and best_gap is not None and best_gap > 0.0

    return {
        "schema_version": "phase5p5_repair5g0_c_channel_semantic_gap_v1",
        "created_at": datetime.now().isoformat(),
        "g0_commit": G0_COMMIT,
        "inputs": {
            "g0_summary_json": str(args.g0_summary_json),
            "g0_summary_csv": str(args.g0_summary_csv),
            "g0_by_map_agent_csv": str(args.g0_by_map_agent_csv),
            "f4_ranking_csv": str(args.f4_ranking_csv),
            "ltm_cpp": str(args.ltm_cpp),
            "ltm_hpp": str(args.ltm_hpp),
        },
        "code_audit": code,
        "g0_dev_probe": {
            "row_count": g0_summary.get("row_count"),
            "missing_rows": g0_summary.get("missing_rows"),
            "schema_errors": g0_summary.get("schema_errors"),
            "dual_additive_parity_exact": g0_summary.get("dual_additive_parity_exact"),
            "cost_bounds_respected": g0_summary.get("cost_bounds_respected"),
        },
        "method_comparison": {
            "scalar_best_f4_static": scalar_best,
            "dual_c_only_best_f4_observed": dual_best,
            "scalar_locked_c100_b100_w075_d090": scalar_locked,
            "dual_c_only_locked_f4": dual_locked,
            "f4_full_lattice_best": f4_best,
            "best_f4_scalar_vs_dual_mean_gap": best_gap,
            "locked_scalar_vs_dual_mean_gap": locked_gap,
        },
        "answers": {
            "do_committed_progress_events_update_only_f_in_g0": c_only_ignored_progress,
            "do_dual_c_only_alpha_flow_zero_candidates_ignore_committed_progress": c_only_ignored_progress,
            "does_this_explain_scalar_vs_dual_c_only_mismatch": explains_mismatch,
            "is_g0_reduced_c_semantics_not_scalar_f4_c_channel": c_only_ignored_progress,
        },
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    answers = summary["answers"]
    comparison = summary["method_comparison"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.0 C-Channel Semantic Gap\n\n")
        handle.write("This report audits why G0 C-only dual-channel candidates were not scalar-equivalent to Repair5F bounded UpdateParams.\n\n")
        handle.write("## Answers\n\n")
        for key, value in answers.items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Evidence\n\n")
        handle.write("- G0 was analyzed at commit `85636b4` where possible via `git show`.\n")
        handle.write(f"- G0 committed-progress updates only F: `{summary['code_audit']['g0_committed_progress_updates_only_flow']}`\n")
        handle.write(f"- Current code has `alpha_cong_commit_progress`: `{summary['code_audit']['current_code_has_alpha_cong_commit_progress']}`\n")
        handle.write(f"- scalar best F4 mean delta: `{comparison['scalar_best_f4_static'].get('mean_delta_ratio_vs_ltm')}`\n")
        handle.write(f"- dual C-only best-F4-observed mean delta: `{comparison['dual_c_only_best_f4_observed'].get('mean_delta_ratio_vs_ltm')}`\n")
        handle.write(f"- scalar-vs-dual best gap: `{comparison['best_f4_scalar_vs_dual_mean_gap']}`\n")
        handle.write(f"- locked scalar-vs-dual gap: `{comparison['locked_scalar_vs_dual_mean_gap']}`\n\n")
        handle.write("## Interpretation\n\n")
        handle.write(
            "G0 tested a reduced C-channel semantics for committed progress edges. "
            "When `alpha_flow_commit_progress=0`, a committed progress edge did not contribute to either channel, "
            "so the dual C-only controls could not reproduce scalar Repair5F C-only behavior. "
            "This makes G0 a valid negative result for its global-F candidate family, but not a rejection of scalar-equivalent or agent-aware dual-channel LTM.\n\n"
        )
        handle.write("`phase5p5_allowed=false` and `phase6_allowed=false` remain mandatory.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g0-summary-json", type=Path, default=Path(DEFAULT_G0_SUMMARY_JSON))
    parser.add_argument("--g0-summary-csv", type=Path, default=Path(DEFAULT_G0_SUMMARY_CSV))
    parser.add_argument("--g0-by-map-agent-csv", type=Path, default=Path(DEFAULT_G0_BY_MAP_AGENT))
    parser.add_argument("--f4-ranking-csv", type=Path, default=Path(DEFAULT_F4_RANKING))
    parser.add_argument("--ltm-cpp", type=Path, default=Path(DEFAULT_LTM_CPP))
    parser.add_argument("--ltm-hpp", type=Path, default=Path(DEFAULT_LTM_HPP))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    summary = build_summary(args)
    summary_path = resolve(args.summary_json, root)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(resolve(args.report, root), summary)
    print(json.dumps(summary["answers"], sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
