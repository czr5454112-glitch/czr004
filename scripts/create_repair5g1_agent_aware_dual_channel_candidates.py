"""Create the Repair5G.1 agent-aware dual-channel LTM candidate lattice."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_CSV = "outputs/tables/phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice_summary.json"


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    runtime_method: str
    enable_dual_channel: bool
    alpha_cong_commit_progress: float
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
    goal_projection_mode: str
    flow_shield_beta: float
    max_flow_shield: float
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


def token(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def scalar_params(rule_id: str) -> tuple[float, float, float, float]:
    if rule_id == "additive":
        return (1.0, 1.0, 1.0, 1.0)
    parts = rule_id.split("_")
    if len(parts) != 4:
        raise ValueError(rule_id)
    return tuple(float(part[1:]) / 100.0 for part in parts)  # type: ignore[return-value]


def _candidate(
    candidate_id: str,
    runtime_method: str,
    *,
    rule_id: str = "additive",
    enable_dual_channel: bool = True,
    alpha_cong_commit_progress: float | None = None,
    alpha_cong_commit_nonprogress: float | None = None,
    alpha_cong_block: float | None = None,
    alpha_cong_wait_progress: float | None = None,
    alpha_cong_wait_nonprogress: float | None = None,
    alpha_flow_commit_progress: float = 0.0,
    alpha_flow_wait_progress: float = 0.0,
    rho_cong_decay: float | None = None,
    rho_flow_decay: float = 1.0,
    lambda_cong: float = 1.0,
    lambda_flow: float = 0.0,
    min_edge_cost: float = 0.25,
    max_edge_cost: float = 11.0,
    goal_projection_mode: str = "none",
    flow_shield_beta: float = 0.0,
    max_flow_shield: float = 0.0,
    notes: str,
    component: str,
) -> Candidate:
    c, b, w, d = scalar_params(rule_id)
    return Candidate(
        candidate_id=candidate_id,
        runtime_method=runtime_method,
        enable_dual_channel=enable_dual_channel,
        alpha_cong_commit_progress=c if alpha_cong_commit_progress is None else alpha_cong_commit_progress,
        alpha_cong_commit_nonprogress=c
        if alpha_cong_commit_nonprogress is None
        else alpha_cong_commit_nonprogress,
        alpha_cong_block=b if alpha_cong_block is None else alpha_cong_block,
        alpha_cong_wait_progress=w if alpha_cong_wait_progress is None else alpha_cong_wait_progress,
        alpha_cong_wait_nonprogress=w
        if alpha_cong_wait_nonprogress is None
        else alpha_cong_wait_nonprogress,
        alpha_flow_commit_progress=alpha_flow_commit_progress,
        alpha_flow_wait_progress=alpha_flow_wait_progress,
        rho_cong_decay=d if rho_cong_decay is None else rho_cong_decay,
        rho_flow_decay=rho_flow_decay,
        lambda_cong=lambda_cong,
        lambda_flow=lambda_flow,
        min_edge_cost=min_edge_cost,
        max_edge_cost=max_edge_cost,
        goal_projection_mode=goal_projection_mode,
        flow_shield_beta=flow_shield_beta,
        max_flow_shield=max_flow_shield,
        notes=notes,
        diagnostic_only=True,
        phase5p5_allowed=False,
        phase6_allowed=False,
        component=component,
    )


def build_candidates() -> list[Candidate]:
    candidates: list[Candidate] = [
        _candidate(
            "dcltm_additive_parity",
            "repair5g_dual_additive_parity",
            enable_dual_channel=False,
            alpha_cong_commit_progress=0.0,
            alpha_flow_commit_progress=0.0,
            notes="Legacy exact additive LTM parity control.",
            component="parity",
        )
    ]

    c_only_rules = [
        "additive",
        "c100_b100_w075_d090",
        "c125_b125_w075_d095",
        "c100_b125_w075_d100",
        "c100_b100_w075_d095",
        "c100_b100_w100_d090",
        "c100_b100_w075_d100",
    ]
    for rule in c_only_rules:
        candidates.append(
            _candidate(
                f"dcltm_c_equiv_{rule}",
                f"repair5g_dual_c_equiv_{rule}",
                rule_id=rule,
                notes=f"Scalar-equivalent C-only dual channel for `{rule}`.",
                component="c_equiv",
            )
        )

    flow_bases = [
        "additive",
        "c125_b125_w075_d095",
        "c100_b125_w075_d100",
        "c100_b100_w075_d095",
    ]
    for rule in flow_bases:
        for lambda_flow in [0.01, 0.025, 0.05, 0.10]:
            candidates.append(
                _candidate(
                    f"global_{rule}_lf{token(lambda_flow)}_min0p75",
                    f"repair5g1_global_{rule}_lf{token(lambda_flow)}_min0p75",
                    rule_id=rule,
                    alpha_flow_commit_progress=1.0,
                    lambda_flow=lambda_flow,
                    min_edge_cost=0.75,
                    goal_projection_mode="none",
                    notes="G0-style global F small-lambda control.",
                    component="global_f_small_lambda",
                )
            )

    for rule in flow_bases:
        for lambda_flow in [0.01, 0.025, 0.05, 0.10, 0.20]:
            for min_cost in [0.50, 0.75, 1.00]:
                candidates.append(
                    _candidate(
                        f"agent_{rule}_lf{token(lambda_flow)}_min{token(min_cost)}",
                        f"repair5g1_agent_{rule}_lf{token(lambda_flow)}_min{token(min_cost)}",
                        rule_id=rule,
                        alpha_flow_commit_progress=1.0,
                        lambda_flow=lambda_flow,
                        min_edge_cost=min_cost,
                        goal_projection_mode="agent_progress",
                        notes="Agent-aware F discount projected by current-agent goal progress.",
                        component="agent_progress_f",
                    )
                )

    for rule in ["c125_b125_w075_d095", "c100_b125_w075_d100", "c100_b100_w075_d095"]:
        for beta in [0.05, 0.10, 0.20, 0.35]:
            for max_shield in [0.25, 0.50, 0.75]:
                candidates.append(
                    _candidate(
                        f"shield_{rule}_beta{token(beta)}_max{token(max_shield)}",
                        f"repair5g1_shield_{rule}_beta{token(beta)}_max{token(max_shield)}",
                        rule_id=rule,
                        alpha_flow_commit_progress=1.0,
                        min_edge_cost=1.0,
                        goal_projection_mode="flow_shield",
                        flow_shield_beta=beta,
                        max_flow_shield=max_shield,
                        notes="Flow-shield C penalty reducer on current-agent progress edges only.",
                        component="flow_shield",
                    )
                )

    for rule in flow_bases:
        for wait_progress, wait_nonprogress in [(0.25, 1.0), (0.50, 1.0), (0.75, 1.25)]:
            candidates.append(
                _candidate(
                    f"wait_{rule}_wp{token(wait_progress)}_wn{token(wait_nonprogress)}",
                    f"repair5g1_wait_{rule}_wp{token(wait_progress)}_wn{token(wait_nonprogress)}",
                    rule_id=rule,
                    alpha_cong_wait_progress=wait_progress,
                    alpha_cong_wait_nonprogress=wait_nonprogress,
                    notes="Wait-gated C-only control with reduced progress-exit wait spillover.",
                    component="wait_gated",
                )
            )

    candidates.append(
        _candidate(
            "random_static_diagnostic",
            "repair5g1_random_static_diagnostic",
            rule_id="c080_b120_w060_d095",
            alpha_flow_commit_progress=1.0,
            lambda_flow=0.025,
            min_edge_cost=0.75,
            goal_projection_mode="agent_progress",
            notes="Deterministic random diagnostic candidate; never promotable.",
            component="diagnostic",
        )
    )
    return candidates


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
        "schema_version": "phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice_v1",
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
        handle.write("# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel Candidate Lattice\n\n")
        handle.write("This is diagnostic-only. It does not permit Phase5.5 or Phase6.\n\n")
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
            "| candidate_id | runtime_method | component | mode | lambda_flow | beta | max_shield | min_cost | notes |\n"
        )
        handle.write("|---|---|---|---|---:|---:|---:|---:|---|\n")
        for candidate in candidates:
            handle.write(
                f"| {candidate.candidate_id} | {candidate.runtime_method} | {candidate.component} | "
                f"{candidate.goal_projection_mode} | {candidate.lambda_flow:g} | "
                f"{candidate.flow_shield_beta:g} | {candidate.max_flow_shield:g} | "
                f"{candidate.min_edge_cost:g} | {candidate.notes} |\n"
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
