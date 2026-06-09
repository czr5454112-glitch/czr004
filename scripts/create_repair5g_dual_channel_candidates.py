"""Create the Repair5G goal-aware dual-channel LTM candidate lattice."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CSV = "outputs/tables/phase5p5_repair5g_dual_channel_candidate_lattice.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g_dual_channel_candidate_lattice_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g_dual_channel_candidate_lattice_summary.json"


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    runtime_method: str
    enable_dual_channel: bool
    alpha_cong_commit_nonprogress: float
    alpha_cong_block: float
    alpha_cong_wait_progress: float
    alpha_cong_wait_nonprogress: float
    alpha_flow_commit_progress: float
    alpha_flow_wait_progress: float
    rho_cong_decay: float
    rho_flow_decay: float
    lambda_cong: float
    lambda_flow: float
    min_edge_cost: float
    max_edge_cost: float
    notes: str
    diagnostic_only: bool
    phase5p5_allowed: bool
    phase6_allowed: bool
    component: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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


def _candidate(
    candidate_id: str,
    runtime_method: str,
    *,
    enable_dual_channel: bool = True,
    alpha_cong_commit_nonprogress: float = 0.0,
    alpha_cong_block: float = 1.0,
    alpha_cong_wait_progress: float = 1.0,
    alpha_cong_wait_nonprogress: float = 1.0,
    alpha_flow_commit_progress: float = 1.0,
    alpha_flow_wait_progress: float = 0.0,
    rho_cong_decay: float = 1.0,
    rho_flow_decay: float = 1.0,
    lambda_cong: float = 1.0,
    lambda_flow: float = 0.25,
    min_edge_cost: float = 0.25,
    max_edge_cost: float = 11.0,
    notes: str,
    component: str,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id,
        runtime_method=runtime_method,
        enable_dual_channel=enable_dual_channel,
        alpha_cong_commit_nonprogress=alpha_cong_commit_nonprogress,
        alpha_cong_block=alpha_cong_block,
        alpha_cong_wait_progress=alpha_cong_wait_progress,
        alpha_cong_wait_nonprogress=alpha_cong_wait_nonprogress,
        alpha_flow_commit_progress=alpha_flow_commit_progress,
        alpha_flow_wait_progress=alpha_flow_wait_progress,
        rho_cong_decay=rho_cong_decay,
        rho_flow_decay=rho_flow_decay,
        lambda_cong=lambda_cong,
        lambda_flow=lambda_flow,
        min_edge_cost=min_edge_cost,
        max_edge_cost=max_edge_cost,
        notes=notes,
        diagnostic_only=True,
        phase5p5_allowed=False,
        phase6_allowed=False,
        component=component,
    )


def build_candidates() -> list[Candidate]:
    return [
        _candidate(
            "dcltm_additive_parity",
            "repair5g_dual_additive_parity",
            enable_dual_channel=False,
            alpha_cong_commit_nonprogress=1.0,
            alpha_cong_block=1.0,
            alpha_cong_wait_progress=1.0,
            alpha_cong_wait_nonprogress=1.0,
            alpha_flow_commit_progress=0.0,
            lambda_cong=1.0,
            lambda_flow=0.0,
            notes="Exact additive LTM parity control; routes through legacy UpdateLTM semantics.",
            component="parity",
        ),
        _candidate(
            "dcltm_c_only_locked_f4",
            "repair5g_dual_c_only_locked_f4",
            alpha_cong_commit_nonprogress=1.0,
            alpha_cong_block=1.0,
            alpha_cong_wait_progress=0.75,
            alpha_cong_wait_nonprogress=0.75,
            alpha_flow_commit_progress=0.0,
            rho_cong_decay=0.90,
            lambda_flow=0.0,
            notes="C-only diagnostic matching the failed locked Repair5F static rule.",
            component="c_only",
        ),
        _candidate(
            "dcltm_c_only_best_f4_observed",
            "repair5g_dual_c_only_best_f4_observed",
            alpha_cong_commit_nonprogress=1.25,
            alpha_cong_block=1.25,
            alpha_cong_wait_progress=0.75,
            alpha_cong_wait_nonprogress=0.75,
            alpha_flow_commit_progress=0.0,
            rho_cong_decay=0.95,
            lambda_flow=0.0,
            notes="C-only diagnostic matching the best observed F4 static candidate; not promotable.",
            component="c_only",
        ),
        _candidate(
            "dcltm_flow_only_025",
            "repair5g_dual_flow_only_025",
            alpha_cong_commit_nonprogress=0.0,
            alpha_cong_block=0.0,
            alpha_cong_wait_progress=0.0,
            alpha_cong_wait_nonprogress=0.0,
            lambda_cong=0.0,
            lambda_flow=0.25,
            notes="Flow-only committed goal-progress guidance with lambda_flow=0.25.",
            component="f_only",
        ),
        _candidate(
            "dcltm_flow_only_050",
            "repair5g_dual_flow_only_050",
            alpha_cong_commit_nonprogress=0.0,
            alpha_cong_block=0.0,
            alpha_cong_wait_progress=0.0,
            alpha_cong_wait_nonprogress=0.0,
            lambda_cong=0.0,
            lambda_flow=0.50,
            notes="Flow-only committed goal-progress guidance with lambda_flow=0.50.",
            component="f_only",
        ),
        _candidate(
            "dcltm_block_wait_cong_flow025",
            "repair5g_dual_block_wait_cong_flow025",
            lambda_flow=0.25,
            notes="Blocked/wait congestion plus committed goal-progress flow, lambda_flow=0.25.",
            component="c_plus_f",
        ),
        _candidate(
            "dcltm_block_wait_cong_flow050",
            "repair5g_dual_block_wait_cong_flow050",
            lambda_flow=0.50,
            notes="Blocked/wait congestion plus committed goal-progress flow, lambda_flow=0.50.",
            component="c_plus_f",
        ),
        _candidate(
            "dcltm_goal_gated_wait_025",
            "repair5g_dual_goal_gated_wait_025",
            alpha_cong_wait_progress=0.25,
            alpha_cong_wait_nonprogress=1.0,
            lambda_flow=0.25,
            notes="Goal-gated wait: weakly penalize progress exits, strongly penalize non-progress exits.",
            component="goal_gated_wait",
        ),
        _candidate(
            "dcltm_goal_gated_wait_050",
            "repair5g_dual_goal_gated_wait_050",
            alpha_cong_wait_progress=0.25,
            alpha_cong_wait_nonprogress=1.0,
            lambda_flow=0.50,
            notes="Goal-gated wait with stronger flow discount.",
            component="goal_gated_wait",
        ),
        _candidate(
            "dcltm_balanced_decay",
            "repair5g_dual_balanced_decay",
            rho_cong_decay=0.95,
            rho_flow_decay=0.95,
            lambda_flow=0.25,
            notes="Balanced C/F decay at 0.95 with lambda_flow=0.25.",
            component="c_plus_f_decay",
        ),
    ]


def write_csv(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(candidates[0]).keys()) if candidates else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(asdict(candidate))


def build_summary(candidates: list[Candidate], csv_path: Path, report: Path, root: Path) -> dict[str, Any]:
    return {
        "schema_version": "phase5p5_repair5g_dual_channel_candidate_lattice_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "candidate_count": len(candidates),
        "candidate_ids": [candidate.candidate_id for candidate in candidates],
        "runtime_methods": [candidate.runtime_method for candidate in candidates],
        "component_counts": {
            component: sum(1 for candidate in candidates if candidate.component == component)
            for component in sorted({candidate.component for candidate in candidates})
        },
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "outputs": {"csv": rel(csv_path, root), "report": rel(report, root)},
    }


def write_report(path: Path, summary: dict[str, Any], candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G Dual-Channel Candidate Lattice\n\n")
        handle.write("This is a diagnostic-only representation lattice for goal-aware dual-channel LTM.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- solver_semantic_changes: `false`\n")
        handle.write("- learned_restart_enabled: `false`\n")
        handle.write("- action_prediction_enabled: `false`\n\n")
        handle.write("## Summary\n\n")
        handle.write(f"- candidate_count: `{summary['candidate_count']}`\n")
        handle.write(f"- components: `{summary['component_counts']}`\n\n")
        handle.write("## Candidates\n\n")
        handle.write(
            "| candidate_id | runtime_method | component | dual | lambda_cong | lambda_flow | "
            "rho_cong | rho_flow | notes |\n"
        )
        handle.write("|---|---|---|---:|---:|---:|---:|---:|---|\n")
        for candidate in candidates:
            handle.write(
                "| "
                f"{candidate.candidate_id} | "
                f"{candidate.runtime_method} | "
                f"{candidate.component} | "
                f"{candidate.enable_dual_channel} | "
                f"{candidate.lambda_cong:g} | "
                f"{candidate.lambda_flow:g} | "
                f"{candidate.rho_cong_decay:g} | "
                f"{candidate.rho_flow_decay:g} | "
                f"{candidate.notes} |\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    csv_path = resolve(args.output_csv, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    candidates = build_candidates()
    write_csv(csv_path, candidates)
    summary = build_summary(candidates, csv_path, report, root)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary, candidates)
    print(json.dumps({"csv": rel(csv_path, root), "report": rel(report, root), "summary_json": rel(summary_json, root)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
